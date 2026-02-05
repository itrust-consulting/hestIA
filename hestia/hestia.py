import os
import json
import re
import requests
import gradio as gr
from datetime import datetime
from threading import Lock

import hestia.settings as settings
import hestia.agent as bk

# ---- Config ----
CONTEXT_SIZE = settings.DEFAULT_CONTEXT_SIZE  # set to your DEFAULT_CONTEXT_SIZE
REQUEST_TIMEOUT = settings.REQUEST_TIMEOUT # (connect, read)
# --- Configuration ---
DB_URL = settings.DB_URL  
LLM_URL = settings.LLM_URL

DEFAULT_MODELS = settings.DEFAULT_MODELS
DEFAULT_EMBEDDING_MODEL = settings.DEFAULT_EMB_MODEL

EMBED_RE = re.compile(r"(?:^|[-_:])embed(?:$|[-_:])|embedding|nomic-embed|mxbai-embed|all-minilm|bge-|e5-",
                      re.IGNORECASE)

# ==================================================================
_lock = Lock()

def store_feedback(feedback: dict):
    os.makedirs(settings.APP_DATA, exist_ok=True)
    line = json.dumps(feedback, ensure_ascii=False)
    with _lock:
        with open(settings.REQ_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")


def handle_requests(r_type, level, description, contact, conversation = None):
    feedback = {
        "type": str(r_type),
        "level": str(level),
        "description": str(description),
        "contact": str(contact),
        "timestamp": datetime.now().strftime("%Y-%m-%d")}
    
    if conversation:
        feedback["conversation"] = str(conversation)
    store_feedback(feedback)
    gr.Info("✅ Thanks for your submission! We’ve received your feedback.", duration=3)

# ==================================================================

"""STUUUUPID"""
# initialize endpoints
LLM_Client = bk.HttpClient(LLM_URL)
DB_Client = bk.HttpClient(DB_URL)

llm = bk.OllamaProvider(LLM_Client)
db = bk.QdrantDB(DB_Client)
# Initialize whatever you want to call it
generator = bk.Generator(llm, model=settings.DEFAULT_GEN_MODEL)
embedder = bk.Embedder(llm, model=settings.DEFAULT_EMB_MODEL)
reranker = bk.Reranker(llm, model=settings.DEFAULT_RRK_MODEL)

retriever = bk.Retriever(db)

ENDPOINTS = {
        "generate": generator,
        "embed": embedder,
        "rerank": reranker,
        "retrieve": retriever
    }

router = bk.Router(ENDPOINTS)
constructor = bk.Constructor()

request = bk.RequestHandler()

# ---- Format requests ----

def build_raw_request(
    *,
    type: str,
    body: dict,
    execution: dict | None = None,
) -> dict:
    """
    Generic raw request envelope builder.

    - `type`: request/event type ("rag", "chat", "upsert", ...)
    - `body`: request-specific intent payload (opaque to frontend)
    - `execution`: optional execution overrides (opaque to frontend)

    No validation. No defaults. No schemas.
    """
    return {
        "type": type,
        "body": body,
        "execution": execution or {},
    }

# ---- RAG-Pipeline START ----

def embed(data, model=DEFAULT_EMBEDDING_MODEL):
    response = requests.post(
        f"{LLM_URL}/api/embed",
        json={"model": model, "input": data},
    )
    if len(response.json()["embeddings"]) > 0:
        return response.json()["embeddings"][0]
    else:
        return None

def query(prompt, collection, model=DEFAULT_EMBEDDING_MODEL, limit=3):
    """
    TODO:
    - include more sophistacted query options.
    
    :param prompt: Description
    :param collection: Description
    :param model: Description
    """
    # adjust for qdrant to handle properly
    #adjusted_prompt = f"Represent this sentence for searching relevant passages: {prompt}"
    embedding = embed(prompt, model=model)

    results = db.query(collection_name=collection, 
                                  query=embedding,
                                  using="Default",
                                  with_payload=True,
                                  score_threshold=0.75,
                                  limit=limit)
    print(results)
    return results

def format_retrieved_data(retrieved_data):

    formatted_data = []
    for point in retrieved_data.points:
        payload = point.payload

        title = payload.get("title", "Untitled Document")
        source = payload.get("source")
        content = payload.get("content")

        # Structure each retrieved item clearly for the LLM
        article_text = f"""
        [SOURCE: {source}]
        Title: {title}
        Content: {content}
        """
        formatted_data.append(article_text.strip())

    return "\n\n".join(formatted_data)

def build_rag_message(user_message, retrieved_data):

    relevant_articles_str = format_retrieved_data(retrieved_data)

    augmented_prompt = f"""
    You are an assistant with access to a knowledge base of Markdown documents. Below are the most relevant excerpts retrieved from that database.
    <retrieved-data>
    {relevant_articles_str}
    </retrieved-data>
    Instruction:
    - Using only the retrieved data above, answer the user's question. 
    - If the retrieved data is insufficient, say so explicitly.
    - After generating your response, always:
        1. Explicitly list the sources used in the format:
        Sources:
        - [SOURCE]
        2. Append the all retrieved articles in an expandable <details> section, formatted as:
        <details>
        <summary><b>Show retrieved articles</b></summary>
        <ul>
            <li><strong>[SOURCE: <TAG>]</strong></li>
            <li>Source content</li>
        </ul>
        </details>


    <user-prompt>
        {user_message}
    </user-prompt>
    """
    return {"role": "system", "content": augmented_prompt}

# --- RAG-Pipeline END ---


def get_databases():
    try:
        resp = db.get_collections()
        return [c.name for c in resp.collections]
    except Exception as e:
        print(f"[DB ERROR] {e}")
        return []

def get_ollama_models(filter_embeddings=True):
    try:
        models = llm.models
        if filter_embeddings:
            models = [m for m in models if not EMBED_RE.search(m)]
        return models
    except Exception as e:
        print(f"[LLM ERROR] {e}")
        return []

def stream_ollama_chat(model, messages, context_size):
    """
    Stream response from Ollama /api/chat.
    Ollama streams newline-delimited JSON (application/x-ndjson).
    Each streamed object contains message.content chunks and done flags. 
    """
    url = f"{LLM_URL}/api/chat"
    payload = {
        "model": model,
        "messages": messages,
        "stream": True,
        "options": {"num_ctx": context_size},
    }

    with requests.post(url, json=payload, stream=True, timeout=REQUEST_TIMEOUT) as r:
        r.raise_for_status()
        partial = ""
        for line in r.iter_lines(decode_unicode=True):
            if not line:
                continue
            obj = json.loads(line)
            chunk = obj.get("message", {}).get("content", "")
            if chunk:
                partial += chunk
                yield partial
            if obj.get("done"):
                break

def chat_interface(message, history, model, context, 
                   enable_rag, collection, mode, retrieval_limit, score_threshold):
    """
    Gradio ChatInterface callback.
    """
    # Non-RAG chat: send full message history to Ollama /api/chat
    messages = []
    for h in history or []:
        if isinstance(h, dict) and "role" in h and "content" in h:
            messages.append({"role": h["role"], "content": h["content"][0]["text"]})

    # If RAG is enabled, augment message with retrieved context
    if enable_rag:
        # 1. retrieve mode [simple, extract, hyDE, q2e]
        # 2. retrieve the collection to query. Backend to resolve 'using' based on selected
        # collection and mode.
        # 3. set query options
        req = build_raw_request(type="rag", body={"query": message, "collection": collection, "mode": mode})

        resp, ctx = request.handle(req)
        plan = constructor.resolve(resp, ctx)
        retrieved_data = router.route(plan)
        #retrieved_data = query(message, collection=collection, limit=retrieval_limit)
        #formatted_data = format_retrieved_data(retrieved_data)
        augmented_message = build_rag_message(message, retrieved_data)

        # add new system message including the retrieved context + user message
        messages.append(augmented_message)
    else:
        messages.append({"role": "user", "content": message})

    # Stream tokens to the UI
    yield from stream_ollama_chat(model=model, messages=messages, context_size=context)



# ---- UI ----
def refresh_models():
    return gr.update(choices=get_ollama_models(), value=None)

def refresh_collections():
    return gr.update(choices=get_databases(), value=None)


with gr.Blocks(title="HestIA", fill_height=True, fill_width=True) as app:

    state = gr.State([])
    gr.Markdown("## itrust local AI - HestIA")

    with gr.Row():
        with gr.Column(scale=1, visible=True) as settings_panel:
            
            model = gr.Dropdown(choices=DEFAULT_MODELS, label="Model", interactive=True)

            context = gr.Slider(4096, 8 * 4096, value=CONTEXT_SIZE, step=4096,
                                interactive=True, label="Context window",
                                visible=False)
            
            with gr.Row():
                enable_rag = gr.Checkbox(label="RAG", value=False)

            with gr.Group(visible=False) as rag_settings:
                mode = gr.Dropdown(choices=bk._AVAILABLE_MODES, 
                                label="Retrieval Mode", 
                                interactive=True)
                collection = gr.Dropdown(choices=["itrust ISMS"], 
                                        label="Corpus",
                                        interactive=True)
                # currently hidden
                retrieval_limit = gr.Number(value=10, precision=0, 
                                            label="Top-K",
                                            interactive=True, 
                                            maximum=20,
                                            visible=False)
                score_threshold = gr.Number(value=0.2, precision=1,
                                            label="Score Threshold",
                                            interactive=True,
                                            maximum=1.0,
                                            visible=False)


            fm = gr.Button("Report / Request")
            with gr.Group(visible=False) as form:
                with gr.Row():
                    request_type = gr.Radio(
                        choices=["Bug Report", "Feature Request"],
                        value="Bug Report",
                        show_label=False,
                        elem_id="radio_l"
                    )
                    
                with gr.Group() as bug_form:
                    gr.Markdown("### Bug Report")
                    b_type = gr.CheckboxGroup(
                            choices=[
                                "Hallucination",
                                "Retrieval Quality",
                                "Crash",
                                "Performance",
                                "Other",
                            ], 
                            label="Issue type(s)",
                            elem_id = "issue_type_group",
                        )
                    b_level = gr.Radio(
                        choices=["Low", "Medium", "High", "Critical"],
                        label="Severity",
                        elem_id = "radio_s",
                    )
                    b_description = gr.Textbox(
                        label="What went wrong?",
                        lines=4,
                    )
                    b_contact = gr.Textbox(
                        label="Issuer (Optional)",
                    )

                with gr.Group() as feat_form:
                    gr.Markdown("### Feature Request")
                    f_type = gr.CheckboxGroup(
                            choices=[
                                "Retrieval/Search",
                                "Answer quality / reasoning",
                                "Transparency (sources/citations)",
                                "Controls / settings",
                                "UX / usability",
                                "Export / integration",
                                "Other",
                            ],
                            label="Feature type(s)",
                            elem_id = "issue_type_group",
                        )
                    f_level = gr.Radio(
                        choices=["Nice to have", "Important", "Blocking"],
                        label="Priority",
                        value="Important",
                        elem_id = "radio_s",
                    )
                    f_description = gr.Textbox(
                        label="Feature Description",
                        placeholder="Describe the expected behaviour.",
                        lines=4,
                        )
                    
                    f_contact = gr.Textbox(
                            label="Issuer (Optional)",
                        )
                        
                submit_btn = gr.Button("Submit")

        chatbot = gr.Chatbot(buttons=["copy"], 
                             height="calc(100vh - 200px)",)
        with gr.Column(scale=3):
            chat = gr.ChatInterface(
                fn=chat_interface,
                chatbot=chatbot,
                additional_inputs=[model, context, enable_rag, 
                                   collection, mode, retrieval_limit, score_threshold],
                autoscroll=False, 
                fill_height=True,
                #save_history=True,
            )

        enable_rag.change(
            fn=lambda x: gr.Group(visible=x),
            inputs=enable_rag,
            outputs=rag_settings,
        )

        is_vis = gr.State(value=False)

        def toggle_forms(kind):
            return (
                gr.update(visible=(kind == "Bug Report")),
                gr.update(visible=(kind == "Feature Request")),
            )
        
        def handle_submit(request, *args):
            if request == "Bug Report":
                return handle_requests(*args[:5])
            else:
                return handle_requests(*args[-4:])
        
        def vis_state(state, request_type):
            visible = not state
            return (
                not state,
                gr.update(visible=visible),
                gr.update(visible=(request_type == "Bug Report" and visible)),
                gr.update(visible=(request_type == "Feature Request" and visible)),
            )

        fm.click(
            fn=vis_state,
            inputs=[is_vis, request_type],
            outputs=[is_vis, form, bug_form, feat_form],
        )

        request_type.change(
            fn=toggle_forms,
            inputs=request_type,
            outputs=[bug_form, feat_form]
        )

        submit_btn.click(
            fn=handle_submit,
            inputs=[
                request_type,
                b_type, b_level, b_description, b_contact, chatbot,
                f_type, f_level, f_description, f_contact
            ],
            outputs=[]
        )
        
if __name__=="__main__":
    app.launch(theme=gr.themes.Soft(primary_hue="red", secondary_hue="pink", font="Corbel"),
               height="100%", width="calc(100vw)", 
               css_paths=settings.CSS_FILE,
               server_name="0.0.0.0", server_port=7860)