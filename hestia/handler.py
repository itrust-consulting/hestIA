from __future__ import annotations

import json
import logging
import re
import time
import uuid

from hestia.domain.auth.users import now_epoch
from hestia.domain.exceptions import ConfigurationError, ForbiddenError
from hestia.domain.policies.guard import ExecutionPolicy, PolicyDecision, PolicyGuard, PolicyResult
from hestia.domain.rag.graph import ExecutionRequest
from hestia.domain.rag.templater import TemplateRepository, TemplatePlanBuilder
from hestia.domain.rag.types import HybridQuery
from hestia.infrastructure.logging.audit import audit

_log = logging.getLogger("hestia.system")

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
      or \\cite{{key1,key2}} for multiple sources. Use the keys defined in <source-map>.
    - If the retrieved data is insufficient, say so explicitly.
    - Do NOT include a separate sources or references section at the end.

    <user-prompt>
        {user_prompt}
    </user-prompt>
    """


def _make_citekey(source: str, idx: int) -> str:
    stem = re.sub(r'[^a-zA-Z0-9]', '', source.split('/')[-1].split('.')[0])
    return f"{stem or 'src'}{idx}"


def _format_citations(hits: list) -> tuple[dict, list]:
    retrieved_data = []
    source_map = []
    cite_list = []

    for idx, point in enumerate(hits):
        chunk = point.payload
        doc_info = chunk.get("doc_info") or {}
        info = chunk.get("info") or {}
        source = chunk.get("source", "unknown")
        content = chunk.get("content", "")
        subject = doc_info.get("subject", "")
        path = info.get("path", "")
        key = _make_citekey(source, idx + 1)

        retrieved_data.append(f"[{key}: {source}]\n{content}")
        source_map.append(f"- {key}: {source}")
        cite_list.append({
            "key": key,
            "source": source,
            "subject": subject,
            "path": path,
            "excerpt": content,
        })

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


def _extract_used_citekeys(text: str) -> set[str]:
    keys: set[str] = set()
    for group in re.findall(r'\\cite\{([^}]+)\}', text):
        for k in group.split(','):
            keys.add(k.strip())
    return keys


class Runner:

    def __init__(self, container):
        self.container = container
        self.last_slot: dict = {}
        self.node_handlers = {
            "EncodeDense":  self._run_encode_dense,
            "EncodeSparse": self._run_encode_sparse,
            "Retrieve":     self._run_retrieve,
            "Augment":      self._run_augment,
            "Generate":     self._run_generate,
            "Chat":         self._run_chat,
        }

    def run(self, plan, stream=False):
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
            handler(node, slot, stream=False)

        final = nodes[order[-1]]
        handler = self.node_handlers.get(final.type)
        if not handler:
            raise ConfigurationError(f"Node type '{final.type}' is not supported.")
        _log.debug("runner_node", extra={"node_id": final.id, "node_type": final.type, "is_final": True})

        # Expose slot so PersistChat can read _cite_list after intermediates have run
        self.last_slot = slot

        if not stream:
            handler(final, slot, stream=False)
            return slot.get("final")
        return handler(final, slot, stream=True)

    def _run_encode_dense(self, node, slot, stream):
        svc = self._svc("encDense")
        dense = svc.encode(self._resolve(node.inputs.get("data"), slot))
        slot[node.outputs.get("vector", "vector")] = dense

    def _run_encode_sparse(self, node, slot, stream):
        svc = self._svc("encSparse")
        data = self._resolve(node.inputs.get("data"), slot)
        collection = self._resolve(node.inputs.get("collection"), slot)
        slot[node.outputs.get("vector", "vector")] = svc.encode(data, collection)

    def _run_retrieve(self, node, slot, stream):
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
        hits = svc.retrieve(collection, query, options=options)
        slot[node.outputs.get("hits", "hits")] = hits.points

    def _run_augment(self, node, slot, stream):
        prompt = self._resolve(node.inputs.get("prompt"), slot) or ""
        hits = self._resolve(node.inputs.get("hits"), slot) or []
        augmented, cite_list = _build_prompt(prompt, hits)
        slot[node.outputs.get("prompt", "prompt")] = augmented
        slot["_cite_list"] = cite_list

    def _run_generate(self, node, slot, stream):
        svc = self._svc("generate")
        prompt = self._resolve(node.inputs.get("prompt"), slot)
        if stream:
            return svc.generate(prompt=prompt, model=node.model, options=node.options, stream=True)
        resp = svc.generate(prompt=prompt, model=node.model, options=node.options, stream=False)
        slot[node.outputs.get("response", "response")] = resp
        slot["final"] = resp

    def _run_chat(self, node, slot, stream):
        svc = self._svc("generate")
        history = self._resolve(node.inputs.get("history"), slot) or []
        last = self._resolve(node.inputs.get("last_user_message"), slot)
        messages = history + [{"role": "user", "content": last}]
        if stream:
            return svc.chat(messages=messages, model=node.model, options=node.options, stream=True)
        resp = svc.chat(messages=messages, model=node.model, options=node.options, stream=False)
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

    def run(self, plan, stream=False):
        result = self.runner.run(plan, stream=stream)
        if stream:
            return self._wrap_stream(result, self.req)
        self._persist(self.req, result)
        return result

    def _wrap_stream(self, iterable, req: ExecutionRequest):
        final_text = ""
        thinking_text = ""
        cite_list: list = self.runner.last_slot.get("_cite_list", [])

        def generator():
            nonlocal final_text, thinking_text
            # Buffer for splitting inline <think>...</think> tags across chunks
            tag_buf = ""
            in_think = False

            for chunk in iterable:
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
            citations = [c for c in cite_list if c["key"] in used]
            c_id, user_msg_id, assistant_msg_id = self._persist(
                req, final_text, citations=citations, thinking=thinking_text or None
            )
            yield (json.dumps({
                "conversation_id": str(c_id),
                "user_message_id": str(user_msg_id) if user_msg_id else None,
                "assistant_message_id": str(assistant_msg_id),
                "citations": citations,
                "thinking": thinking_text or None,
            }) + "\n").encode("utf-8")

        return generator()

    def _persist(self, req: ExecutionRequest, assistant_reply: str, citations: list | None = None, thinking: str | None = None):
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
            if req.last_user_display_content is not None:
                user_meta["display_content"] = req.last_user_display_content
            if req.last_user_attachments:
                user_meta["attachments"] = req.last_user_attachments
            user_msg_id = self.users.append_conversation_message(
                user_id=user_id, c_id=c_id, role="user", content=req.last_user_message,
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
        self.runner = Runner(container)

    def resolve(self, req: ExecutionRequest, stream: bool = False):
        result: PolicyResult = self.policy.check(req)

        if result.decision == PolicyDecision.DENY:
            raise ForbiddenError(result.msg or "Access denied.")

        if result.decision == PolicyDecision.FILTER:
            req.query_kwargs = req.query_kwargs or {}
            req.query_kwargs["filters"] = result.filters

        template = self.TEMPLATE_MAP[req.exec_type]
        graph = self.builder.build(req, template)

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

        runner = PersistChat(self.runner, req) if req.save_chat else self.runner

        if stream:
            return runner.run(graph, stream=True)

        t0 = time.perf_counter()
        response = runner.run(graph, stream=False)
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
