import json
from fastapi.exceptions import HTTPException

from hestia.templater import TemplateRepository, TemplatePlanBuilder
from hestia.schemas.api import ExecutionRequest, HybridQuery
from hestia.utils.policies import PolicyDecision, PolicyResult, PolicyGuard

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
    - Use citations for replies that use retrieved data using comma-separated citation keys [1, 2, 3, ...].
    - Use the numbering in <source-map>. If a sentence uses multiple sources, include all citation keys.
    - If the retrieved data is insufficient, say so explicitly.
    - At the end, always include:

    {sources_block}

    <user-prompt>
        {user_prompt}
    </user-prompt>
    """

def _format_citations(hits: list[dict[str, str]]) -> dict[str, str]:
    """
    Build:
    - retrieved_data: readable block for prompt
    - source_map: [n]: SOURCE (for clarity)
    - sources_block: Markdown 'Sources:' block like:
        Sources:
        1: SOURCE-1
        2: SOURCE-2
        ...
    - retrieved_details_items: <li><strong>[SOURCE: <n>]</strong></li> <li>snippet</li>
    """

    retrieved_data = []
    source_map = []
    sources_block = ["Source:"]

    for idx, point in enumerate(hits):
        id = idx + 1
        chunk = point.payload
        retrieved_data.append(f"[Source {id}: {chunk['source']}]\n{chunk['content']}")
        source_map.append(f"- [{id}]: {chunk['source']}")
        sources_block.append(f"- **[{id}]**: {chunk['source']}, \
                                {chunk['doc_info']['subject']}, \
                                {chunk['info']['path']} ")

    return {
        "retrieved_data": "\n\n".join(retrieved_data),
        "source_map": "\n".join(source_map),
        "sources_block": "\n".join(sources_block)
    }

def _build_prompt(prompt: str, hits: list[dict[str, str]]) -> str:
    formatted = _format_citations(hits)
    return RAG_PROMPT.format(
        retrieved_data=formatted["retrieved_data"],
        source_map=formatted["source_map"],
        sources_block=formatted["sources_block"],
        user_prompt=prompt,
    )


class Runner:
    def __init__(self, container):
        self.container = container

        # ---- Node execution dispatch table ----
        self.node_handlers = {
            "EncodeDense": self._run_encode_dense,
            "EncodeSparse": self._run_encode_sparse,
            "Retrieve": self._run_retrieve,
            "Augment": self._run_augment,
            "Generate": self._run_generate,
            "Chat": self._run_chat,
        }

    def run(self, plan, stream=False):
        slot = {}
        order = self._linear_order(plan)
        nodes = {n.id: n for n in plan.nodes}

        for nid in order[:-1]:
            node = nodes[nid]
            handler = self.node_handlers.get(node.type)
            if not handler:
                raise HTTPException(501, f"Node type '{node.type}' not supported.")
            handler(node, slot, stream=False)

        # Final node allowed to be streamed
        final_node = nodes[order[-1]]
        handler = self.node_handlers.get(final_node.type)

        if not handler:
            raise HTTPException(501, f"Streaming for {final_node.type} not supported.")

        if not stream:
            handler(final_node, slot, stream=False)
            return slot.get("final")
        return handler(final_node, slot, stream=stream)

    def _run_encode_dense(self, node, slot, stream):
        svc = self._get_service("encDense")
        data = self._resolve(node.inputs.get("data"), slot)
        dense = svc.encode(data)
        out = node.outputs.get("vector", "vector")
        slot[out] = dense

    def _run_encode_sparse(self, node, slot, stream):
        svc = self._get_service("encSparse")
        data = self._resolve(node.inputs.get("data"), slot)
        collection = self._resolve(node.inputs.get("collection"), slot)
        sparse = svc.encode(data, collection)
        out = node.outputs.get("vector", "vector")
        slot[out] = sparse

    def _run_retrieve(self, node, slot, stream):
        svc = self._get_service("search")
        dense = self._resolve(node.inputs.get("dense"), slot)
        sparse = self._resolve(node.inputs.get("sparse"), slot)

        if dense and sparse:
            query = HybridQuery(dense=dense, sparse=sparse)
        else:
            query = dense or sparse
        if not query:
            raise HTTPException(400, "Retrieve node received no query vector.")

        collection = self._resolve(node.inputs.get("collection"), slot)
        options = self._resolve(node.inputs.get("options"), slot) or {}

        hits = svc.retrieve(collection, query, options=options)
        out = node.outputs.get("hits", "hits")
        slot[out] = hits.points

    def _run_augment(self, node, slot, stream):
        prompt = self._resolve(node.inputs.get("prompt"), slot) or ""
        hits = self._resolve(node.inputs.get("hits"), slot) or []

        augmented = _build_prompt(prompt, hits)
        out = node.outputs.get("prompt", "prompt")
        slot[out] = augmented

    def _run_generate(self, node, slot, stream):
        svc = self._get_service("generate")
        prompt = self._resolve(node.inputs.get("prompt"), slot)
        if stream:
            return svc.generate(prompt=prompt, model=node.model, options=node.options, stream=True)

        resp = svc.generate(prompt=prompt, model=node.model, options=node.options, stream=False)
        out = node.outputs.get("response", "response")
        slot[out] = resp
        slot["final"] = resp

    def _run_chat(self, node, slot, stream):
        svc = self._get_service("generate")
        history = self._resolve(node.inputs.get("history"), slot) or []
        last = self._resolve(node.inputs.get("last_user_message"), slot)

        messages = history + [{"role": "user", "content": last}]

        if stream:
            return svc.chat(messages=messages, model=node.model, options=node.options, stream=True)

        resp = svc.chat(messages=messages, model=node.model, options=node.options, stream=False)
        out = node.outputs.get("response", "response")
        slot[out] = resp
        slot["final"] = resp

    def _get_service(self, name):
        svc = self.container.services.get(name)
        if not svc:
            raise HTTPException(500, detail=f"Service '{name}' not available.")
        return svc

    def _resolve(self, val, slot):
        if isinstance(val, str) and val.startswith("?"):
            return slot.get(val[1:])
        return val

    def _linear_order(self, plan):
        if plan.edges:
            order = [plan.entrypoint]
            nxt = self._next_of(plan, plan.entrypoint)
            while nxt:
                order.append(nxt)
                nxt = self._next_of(plan, nxt)
            return order
        return [n.id for n in plan.nodes]

    def _next_of(self, plan, nid):
        for a, b in plan.edges:
            if a == nid:
                return b
        return None


class PersistChat:
    """
    Wrapper around Runner that persists conversation messages
    using the UserService ("auth" service in your container).
    """

    def __init__(self, runner: Runner, req: ExecutionRequest):
        self.runner = runner
        self.req = req
        self.auth = runner.container.services.get("auth")
        self.users = runner.container.services.get("users")

    def run(self, plan, stream=False):
        # Execute normal runner
        result = self.runner.run(plan, stream=stream)

        if stream:
            return self._wrap_stream(result, self.req)

        # Non-stream: persist immediately
        conversation_id = self._persist(self.req, result)
        return result

    def _wrap_stream(self, iterable, req):
        final_text = ""

        def generator():
            nonlocal final_text
            for chunk in iterable:
                text = self._extract_text(chunk)
                final_text += text
                yield chunk

            conversation_id, user_msg_id, assistant_msg_id = self._persist(req, final_text)

            yield json.dumps({
                "conversation_id": conversation_id.hex(),
                "user_message_id": user_msg_id.hex() if user_msg_id else None,
                "assistant_message_id": assistant_msg_id.hex()
            }).encode("utf-8")


        return generator()

    def _extract_text(self, chunk):
        if isinstance(chunk, dict):
            return chunk.get("content", "") or chunk.get("delta", "")
        return str(chunk)

    def _persist(self, req: ExecutionRequest, assistant_reply):

        user_id = req.user.id.bytes

        if req.conversation_id:
            c_id = bytes.fromhex(req.conversation_id)
        else:
            # Create new conversation
            title = req.conversation_title or req.last_user_message[:40]
            c_id = self.users.create_user_conversation(user_id, title)

        # Persist the user message
        if req.last_user_message:
            user_msg_id = self.users.append_conversation_message(
                c_id=c_id,
                role="user",
                content=req.last_user_message,
                metadata={},
                options=req.model_kwargs or {}
            )

        # Persist assistant reply
        assistant_msg_id = self.users.append_conversation_message(
            c_id=c_id,
            role="assistant",
            content=assistant_reply,
            metadata={},
            options=req.model_kwargs or {}
        )
        return c_id, user_msg_id, assistant_msg_id


class RequestHandler:
    """
    Central orchestrator: compile -> authorize -> optimize -> execute a Plan.
    Constructed once at startup with the Container.
    """
    TEMPLATE_MAP = {
        "generate" :        "./workflows/generate.yaml",
        "rag_generate":     "./workflows/rag_generate.yaml",
        "chat" :            "./workflows/chat.yaml",
        "rag_chat":         "./workflows/rag_chat.yaml",
    }
    def __init__(self, container,  policy: PolicyGuard = None, telemetry=None):
        self.container = container
        self.policy = policy
        self.telemetry = telemetry
        self.builder = TemplatePlanBuilder(TemplateRepository())
        self.runner = Runner(container)

    def resolve(self, req: ExecutionRequest, stream: bool):

        policy_result: PolicyResult = self.policy.check(req)

        if policy_result.decision == PolicyDecision.DENY:
            raise PermissionError(policy_result.msg)

        if policy_result.decision == PolicyDecision.FILTER:
            # inject filter constraints into the ExecutionRequest
            req.query_kwargs = req.query_kwargs or {}
            req.query_kwargs["filters"] = policy_result.filters
    

        runner = self.runner
        template = self.TEMPLATE_MAP[req.exec_type]
        graph = self.builder.build(req, template)
        if req.save_chat:
            runner = PersistChat(runner, req)

        return runner.run(graph, stream=req.stream)
        
