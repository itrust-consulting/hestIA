from __future__ import annotations

import json
import logging
import re
import time
import uuid

from hestia.domain.auth.users import now_epoch
from hestia.domain.chat.context_budget import (
    BudgetCheck, check_context_budget, fetch_budget_inputs, run_compaction,
)
from hestia.domain.exceptions import ConfigurationError, ForbiddenError, HestiaError
from hestia.domain.policies.guard import ExecutionPolicy, PolicyDecision, PolicyGuard, PolicyResult
from hestia.domain.rag.graph import ExecutionRequest
from hestia.domain.rag.templater import TemplateRepository, TemplatePlanBuilder
from hestia.domain.rag.types import HybridQuery
from hestia.infrastructure.logging.audit import audit

CONTEXT_BUDGET_EXEC_TYPES = ("chat", "rag_chat")

_log = logging.getLogger("hestia.system")

# @MRS-038
RAG_PROMPT = """
    You are an assistant with access to an organizations ISMS knowledge base of Markdown documents.
    Below are the most relevant excerpts retrieved from that database.

    <retrieved-data>
        {retrieved_data}
    </retrieved-data>

    <source-map>
        {source_map}
    </source-map>

    Instruction:
    - Use LaTeX-style citations when referencing retrieved data: \\cite{{key}} for a single source,
      or \\cite{{key1,key2}} for multiple sources.
    - IMPORTANT: Use ONLY the numeric keys defined in <source-map>. Do NOT derive keys from
      filenames, document titles, or any other source. The keys are short integers (1, 2, 3, ...).
    - If the retrieved data is insufficient, say so explicitly.
    - Do NOT include a separate sources or references section at the end.

    <user-prompt>
        {user_prompt}
    </user-prompt>
    """


# @MRS-032, @MRS-068
def _format_citations(hits: list) -> tuple[dict, list]:
    retrieved_data = []
    source_map = []
    cite_list = []
    source_to_key: dict[str, str] = {}

    for point in hits:
        chunk = point.payload
        doc_info = chunk.get("doc_info") or {}
        info = chunk.get("info") or {}
        source = chunk.get("source", "unknown")
        content = chunk.get("content", "")

        if source not in source_to_key:
            key = str(len(source_to_key) + 1)
            source_to_key[source] = key
            source_map.append(f"- {key}: {source}")
            cite_list.append({
                "key": key,
                "source": source,
                "subject": doc_info.get("subject", ""),
                "path": info.get("path", ""),
                "excerpt": content,
            })

        retrieved_data.append(f"[{source_to_key[source]}]\n{content}")

    return {
        "retrieved_data": "\n\n".join(retrieved_data),
        "source_map": "\n".join(source_map),
    }, cite_list


def _build_prompt(prompt: str, hits: list) -> tuple[str, list]:
    if not hits:
        return prompt, []
    formatted, cite_list = _format_citations(hits)
    return RAG_PROMPT.format(
        retrieved_data=formatted["retrieved_data"],
        source_map=formatted["source_map"],
        user_prompt=prompt,
    ), cite_list


def _normalize_citekey(key: str) -> str:
    return re.sub(r'[^a-zA-Z0-9]', '', key).lower()


def _extract_used_citekeys(text: str) -> set[str]:
    keys: set[str] = set()
    for group in re.findall(r'\\cite\{([^}]+)\}', text):
        for k in group.split(','):
            keys.add(_normalize_citekey(k.strip()))
    return keys


# @MRS-058
class Runner:

    def __init__(self, container):
        self.container = container
        self.node_handlers = {
            "EncodeDense":  self._run_encode_dense,
            "EncodeSparse": self._run_encode_sparse,
            "Retrieve":     self._run_retrieve,
            "Augment":      self._run_augment,
            "Generate":     self._run_generate,
            "Chat":         self._run_chat,
        }

    # @MRS-058
    async def run(self, plan, stream=False):
        slot = {}
        order = self._linear_order(plan)
        nodes = {n.id: n for n in plan.nodes}
        _log.debug("runner_start", extra={"n_nodes": len(order), "order": order, "stream": stream})

        for nid in order[:-1]:
            node = nodes[nid]
            handler = self.node_handlers.get(node.type)
            if not handler:
                raise ConfigurationError(f"Node type '{node.type}' is not supported.")
            _log.debug("runner_node", extra={"node_id": nid, "node_type": node.type})
            await handler(node, slot, stream=False)

        final = nodes[order[-1]]
        handler = self.node_handlers.get(final.type)
        if not handler:
            raise ConfigurationError(f"Node type '{final.type}' is not supported.")
        _log.debug("runner_node", extra={"node_id": final.id, "node_type": final.type, "is_final": True})

        if not stream:
            await handler(final, slot, stream=False)
            return slot.get("final"), slot
        gen = await handler(final, slot, stream=True)
        return gen, slot

    async def _run_encode_dense(self, node, slot, stream):
        svc = self._svc("encDense")
        dense = await svc.encode(self._resolve(node.inputs.get("data"), slot))
        slot[node.outputs.get("vector", "vector")] = dense

    async def _run_encode_sparse(self, node, slot, stream):
        svc = self._svc("encSparse")
        data = self._resolve(node.inputs.get("data"), slot)
        collection = self._resolve(node.inputs.get("collection"), slot)
        slot[node.outputs.get("vector", "vector")] = svc.encode(data, collection)

    async def _run_retrieve(self, node, slot, stream):
        svc = self._svc("search")
        dense = self._resolve(node.inputs.get("dense"), slot)
        sparse = self._resolve(node.inputs.get("sparse"), slot)
        has_dense  = dense  is not None and len(dense.vector) > 0
        has_sparse = sparse is not None and len(sparse.indices) > 0
        query = HybridQuery(dense=dense, sparse=sparse) if (has_dense and has_sparse) else (dense if has_dense else sparse)
        if not query:
            raise ConfigurationError("Retrieve node received no query vector — check template wiring.")
        collection = self._resolve(node.inputs.get("collection"), slot)
        options = self._resolve(node.inputs.get("options"), slot) or {}
        hits = await svc.retrieve(collection, query, options=options)
        slot[node.outputs.get("hits", "hits")] = hits.points

    # @MRS-033
    async def _run_augment(self, node, slot, stream):
        prompt = self._resolve(node.inputs.get("prompt"), slot) or ""
        hits = self._resolve(node.inputs.get("hits"), slot) or []
        augmented, cite_list = _build_prompt(prompt, hits)
        slot[node.outputs.get("prompt", "prompt")] = augmented
        slot["_cite_list"] = cite_list
        if hits:
            slot["_aug_prompt"] = augmented

    async def _run_generate(self, node, slot, stream):
        svc = self._svc("generate")
        prompt = self._resolve(node.inputs.get("prompt"), slot)
        if stream:
            return await svc.generate(prompt=prompt, model=node.model, options=node.options, stream=True)
        resp = await svc.generate(prompt=prompt, model=node.model, options=node.options, stream=False)
        slot[node.outputs.get("response", "response")] = resp
        slot["final"] = resp

    async def _run_chat(self, node, slot, stream):
        svc = self._svc("generate")
        history = self._resolve(node.inputs.get("history"), slot) or []
        last = self._resolve(node.inputs.get("last_user_message"), slot)
        messages = history + [{"role": "user", "content": last}]
        if stream:
            return await svc.chat(messages=messages, model=node.model, options=node.options, stream=True)
        resp = await svc.chat(messages=messages, model=node.model, options=node.options, stream=False)
        slot[node.outputs.get("response", "response")] = resp
        slot["final"] = resp

    def _svc(self, name):
        svc = self.container.services.get(name)
        if not svc:
            raise ConfigurationError(f"Service '{name}' is not available — check services_to_start config.")
        return svc

    def _resolve(self, val, slot):
        if isinstance(val, str) and val.startswith("?"):
            return slot.get(val[1:])
        return val

    def _linear_order(self, plan) -> list[str]:
        if plan.edges:
            order = [plan.entrypoint]
            nxt = self._next_of(plan, plan.entrypoint)
            while nxt:
                order.append(nxt)
                nxt = self._next_of(plan, nxt)
            return order
        return [n.id for n in plan.nodes]

    def _next_of(self, plan, nid: str) -> str | None:
        for a, b in plan.edges:
            if a == nid:
                return b
        return None


class PersistChat:

    def __init__(self, runner: Runner, req: ExecutionRequest):
        self.runner = runner
        self.req = req
        self.users = runner.container.services.get("users")

    async def run(self, plan, stream=False):
        result, slot = await self.runner.run(plan, stream=stream)
        if stream:
            return self._wrap_stream(result, self.req, slot), slot
        self._persist(self.req, result, slot)
        return result, slot

    def _wrap_stream(self, iterable, req: ExecutionRequest, slot: dict):
        cite_list: list = slot.get("_cite_list", [])

        async def generator():
            final_text = ""
            thinking_text = ""
            # Buffer for splitting inline <think>...</think> tags across chunks
            tag_buf = ""
            in_think = False

            async for chunk in iterable:
                if isinstance(chunk, dict):
                    raw_content = chunk.get("content", "")
                    # reasoning_content from vLLM / Ollama thinking field
                    direct_thinking = chunk.get("thinking", "")
                else:
                    raw_content, direct_thinking = str(chunk), ""

                if direct_thinking:
                    thinking_text += direct_thinking
                    yield (json.dumps({"thinking": direct_thinking}) + "\n").encode("utf-8")

                if raw_content:
                    tag_buf += raw_content
                    # Route tokens between <think>…</think> to thinking stream,
                    # everything outside to content stream.
                    while tag_buf:
                        if in_think:
                            end = tag_buf.find("</think>")
                            if end == -1:
                                thinking_text += tag_buf
                                yield (json.dumps({"thinking": tag_buf}) + "\n").encode("utf-8")
                                tag_buf = ""
                            else:
                                piece = tag_buf[:end]
                                if piece:
                                    thinking_text += piece
                                    yield (json.dumps({"thinking": piece}) + "\n").encode("utf-8")
                                tag_buf = tag_buf[end + len("</think>"):]
                                in_think = False
                        else:
                            start = tag_buf.find("<think>")
                            if start == -1:
                                final_text += tag_buf
                                yield (json.dumps({"content": tag_buf}) + "\n").encode("utf-8")
                                tag_buf = ""
                            else:
                                piece = tag_buf[:start]
                                if piece:
                                    final_text += piece
                                    yield (json.dumps({"content": piece}) + "\n").encode("utf-8")
                                tag_buf = tag_buf[start + len("<think>"):]
                                in_think = True

            used = _extract_used_citekeys(final_text)
            citations = [c for c in cite_list if _normalize_citekey(c["key"]) in used]
            c_id, user_msg_id, assistant_msg_id = self._persist(
                req, final_text, slot, citations=citations, thinking=thinking_text or None
            )
            yield (json.dumps({
                "conversation_id": str(c_id),
                "user_message_id": str(user_msg_id) if user_msg_id else None,
                "assistant_message_id": str(assistant_msg_id),
                "citations": citations,
                "thinking": thinking_text or None,
                **self._usage_fields(req, c_id),
            }) + "\n").encode("utf-8")

        return generator()

    def _usage_fields(self, req: ExecutionRequest, c_id: uuid.UUID) -> dict:
        """Fresh (post-persist) context-usage snapshot for the final stream
        frame. Fail-open — a usage-display glitch must never break the chat
        stream, same reasoning as RequestHandler's budget-check try/except."""
        try:
            settings = self.runner.container.settings
            prior_summary, tail = fetch_budget_inputs(self.users, req.user.id, c_id)
            check = check_context_budget(prior_summary, tail, settings)
            return {
                "used_tokens": check.tokens,
                "max_tokens": settings.max_context_tokens,
                "needs_compaction": check.needs_compaction,
            }
        except Exception:
            _log.warning("context_usage_fields_failed", extra={"conversation_id": str(c_id)})
            return {}

    def _persist(self, req: ExecutionRequest, assistant_reply: str, slot: dict, citations: list | None = None, thinking: str | None = None):
        user_id = req.user.id
        now = now_epoch()
        if req.conversation_id:
            c_id = uuid.UUID(req.conversation_id)
        else:
            title = req.conversation_title or (req.last_user_message or "")[:40]
            c_id = self.users.create_user_conversation(user_id, title)

        user_msg_id = None
        if req.last_user_message:
            user_meta: dict = {}
            aug_prompt = slot.get("_aug_prompt")
            if aug_prompt:
                user_content = aug_prompt
                user_meta["display_content"] = req.last_user_display_content \
                    if req.last_user_display_content is not None else req.last_user_message
            else:
                user_content = req.last_user_message
                if req.last_user_display_content is not None:
                    user_meta["display_content"] = req.last_user_display_content
            if req.last_user_attachments:
                user_meta["attachments"] = req.last_user_attachments
            user_msg_id = self.users.append_conversation_message(
                user_id=user_id, c_id=c_id, role="user", content=user_content,
                metadata=user_meta, options=req.model_kwargs or {}, ts=now,
            )
        assistant_meta: dict = {}
        if citations:
            assistant_meta["citations"] = citations
        if thinking:
            assistant_meta["thinking"] = thinking
        assistant_msg_id = self.users.append_conversation_message(
            user_id=user_id, c_id=c_id, role="assistant", content=assistant_reply,
            metadata=assistant_meta, options=req.model_kwargs or {}, ts=now + 1,
        )
        return c_id, user_msg_id, assistant_msg_id


class RequestHandler:

    TEMPLATE_MAP = {
        "generate":     "./workflows/generate.yaml",
        "rag_generate": "./workflows/rag_generate.yaml",
        "chat":         "./workflows/chat.yaml",
        "rag_chat":     "./workflows/rag_chat.yaml",
    }

    def __init__(self, container, policy: PolicyGuard = None):
        self.container = container
        self.policy = policy or ExecutionPolicy()
        self.builder = TemplatePlanBuilder(TemplateRepository())
        self.builder.preload(list(self.TEMPLATE_MAP.values()))
        self.runner = Runner(container)

    def _context_budget_inputs(self, req: ExecutionRequest):
        """Fetch (prior_summary, tail) for context-budget bookkeeping. Sync —
        the repo/service layer underneath is plain sqlite3, no I/O to await."""
        users = self.container.services.get("users")
        conversation_id = uuid.UUID(req.conversation_id)
        _log.debug("context_budget_inputs_fetch", extra={"conversation_id": str(conversation_id)})
        prior_summary, tail = fetch_budget_inputs(users, req.user.id, conversation_id)
        return users, conversation_id, prior_summary, tail

    def _needs_context_budget(self, req: ExecutionRequest) -> bool:
        return bool(req.conversation_id) and req.exec_type in CONTEXT_BUDGET_EXEC_TYPES

    async def _apply_context_budget_sync(self, req: ExecutionRequest) -> None:
        """Non-streaming path: no stream to show a notice through, so this
        just runs the check + compaction (if needed) and mutates req.history
        in place. Fails open — a bug here must never break the endpoint."""
        _log.debug("context_budget_sync_start", extra={"conversation_id": req.conversation_id})
        try:
            users, conversation_id, prior_summary, tail = self._context_budget_inputs(req)
            check: BudgetCheck = check_context_budget(prior_summary, tail, self.container.settings)
            if check.needs_compaction:
                generator = self.container.services.get("generate")
                req.history = await run_compaction(
                    generator, self.container.settings, users, conversation_id,
                    prior_summary, check.fold, check.keep,
                )
            else:
                req.history = check.history
        except Exception:
            _log.warning("context_budget_failed_fallback", extra={"conversation_id": req.conversation_id})
            # req.history stays whatever the client sent — never break this endpoint over it

    async def resolve(self, req: ExecutionRequest, stream: bool = False):
        result: PolicyResult = self.policy.check(req)

        if result.decision == PolicyDecision.DENY:
            raise ForbiddenError(result.msg or "Access denied.")

        if result.decision == PolicyDecision.FILTER:
            req.query_kwargs = req.query_kwargs or {}
            req.query_kwargs["filters"] = result.filters

        template = self.TEMPLATE_MAP[req.exec_type]

        prompt_len = len(req.prompt or "") + len(req.last_user_message or "")
        user_id = str(req.user.id)

        audit.ai_request(
            user_id=user_id,
            exec_type=req.exec_type,
            model=req.model,
            collection=req.collection,
            prompt_len=prompt_len,
            stream=stream,
        )
        _log.info(
            "ai_request_start",
            extra={"user_id": user_id, "exec_type": req.exec_type,
                   "model": req.model, "collection": req.collection, "stream": stream},
        )

        if stream:
            return self._stream_with_budget_notice(req, template)

        if self._needs_context_budget(req):
            await self._apply_context_budget_sync(req)

        graph = self.builder.build(req, template)
        runner = PersistChat(self.runner, req) if req.save_chat else self.runner

        t0 = time.perf_counter()
        response, _ = await runner.run(graph, stream=False)
        latency_ms = round((time.perf_counter() - t0) * 1000, 1)

        audit.ai_response(
            user_id=user_id,
            exec_type=req.exec_type,
            response_len=len(response or ""),
            latency_ms=latency_ms,
        )
        _log.info("ai_request_done", extra={"user_id": user_id, "exec_type": req.exec_type,
                                            "latency_ms": latency_ms})
        return response

    async def _stream_with_budget_notice(self, req: ExecutionRequest, template: str):
        """Streaming path: runs the context-budget check before building the
        graph. If compaction is needed, emits a {"status": "compacting"}
        frame — a distinct key from {"thinking"/"content"}, so the frontend
        can flip the existing "Thinking" placeholder's label to "Compacting…"
        without any literal status text ever being written into the message
        body. Fails open on any error, same as the sync path."""
        if self._needs_context_budget(req):
            _log.debug("context_budget_stream_start", extra={"conversation_id": req.conversation_id})
            try:
                users, conversation_id, prior_summary, tail = self._context_budget_inputs(req)
                check: BudgetCheck = check_context_budget(prior_summary, tail, self.container.settings)
                if check.needs_compaction:
                    yield (json.dumps({"status": "compacting"}) + "\n").encode("utf-8")
                    generator = self.container.services.get("generate")
                    req.history = await run_compaction(
                        generator, self.container.settings, users, conversation_id,
                        prior_summary, check.fold, check.keep,
                    )
                else:
                    req.history = check.history
            except Exception:
                _log.warning("context_budget_failed_fallback", extra={"conversation_id": req.conversation_id})
                # req.history stays whatever the client sent — never break the stream over this

        graph = self.builder.build(req, template)
        runner = PersistChat(self.runner, req) if req.save_chat else self.runner
        gen, _ = await runner.run(graph, stream=True)
        try:
            async for chunk in gen:
                yield chunk
        except HestiaError as e:
            # Once inside a StreamingResponse body iterator, headers are
            # already sent -- raising here can't produce a clean error
            # response (Starlette's handler hits "response already started").
            # Surface the failure as a normal in-band content frame instead.
            _log.warning("chat_stream_failed", extra={"conversation_id": req.conversation_id})
            yield (json.dumps({"content": f"\n\n⚠️ {e.message}"}) + "\n").encode("utf-8")
