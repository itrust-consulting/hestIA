import os
import json
import re
import requests
import gradio as gr
from datetime import datetime
from threading import Lock
from typing import List, Dict, Any

import hestia.settings as settings
import hestia.agent as bk
import hestia._db as cred_db


# ---- Config ----
CONTEXT_SIZE = settings.DEFAULT_CONTEXT_SIZE  # set to your DEFAULT_CONTEXT_SIZE
REQUEST_TIMEOUT = settings.REQUEST_TIMEOUT # (connect, read)
# --- Configuration ---
DB_URL = settings.DB_URL  
LLM_URL = settings.LLM_URL

MODELS = settings.DEFAULT_MODELS
GEN_MODEL = settings.DEFAULT_GEN_MODEL          # Model used for query expansion
EMB_MODEL = settings.DEFAULT_EMB_MODEL          # Model used for embeddings
RRK_MODEL = settings.DEFAULT_RRK_MODEL          # Model used for reranking

#KEEP_ALIVE = settings.KEEP_ALIVE                # either here or in the default "options": - setting


# ==================================== HELPER FUNCTIONS ==============================================
"""
TODO:
- build_raw_request() basically layer between backend and frontend.
- move format_retrieved_data() to backend
"""

_lock = Lock()

def store_submission(form: dict):
    os.makedirs(settings.APP_DATA, exist_ok=True)
    line = json.dumps(form, ensure_ascii=False)
    with _lock:
        with open(settings.REQ_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")


def handle_form_submission(form_type, level, description, contact, conversation = None):
    form = {
        "type": str(form_type),
        "level": str(level),
        "description": str(description),
        "contact": str(contact),
        "timestamp": datetime.now().strftime("%Y-%m-%d")}
    
    if conversation:
        form["conversation"] = str(conversation)
    store_submission(form)
    gr.Info("✅ Thanks for your submission! We’ve received your feedback.", duration=3)


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

# ==================================== INITIALIZATION ==============================================

"""
TODO:
- Completely redesign the initialization process...
"""
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


# ==================================== CHAT HANDLER ================================================
"""
TODO:
- move build_rag_message() to backend. 
"""

def build_rag_message(user_message, retrieved_data):

    relevant_articles_str = format_retrieved_data(retrieved_data)

    augmented_prompt = f"""
    You are an assistant with access to a knowledge base of Markdown documents. 
    Below are the most relevant excerpts retrieved from that database.
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


def stream_ollama_chat(model, messages, context_size):
    """
    Stream response from Ollama /api/chat.
    Ollama streams newline-delimited JSON (application/x-ndjson).
    Each streamed object contains message.content chunks and done flags. 
    TODO:
        - forward to HTTPClient
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


# ==================================== UI BUILDER ================================================


def load_messages(user_id):
    
    c_ids = cred_db.list_conversations(user_id)
    print(c_ids)
    messages = []
    for c_id in c_ids:
        messages.append(cred_db.load_messages(user_id=user_id, c_id=c_id["id"]))
    return messages


def do_login(username: str, password: str, session_state):

    ack, msg, id = cred_db.authenticate(username, password)

    if not ack:
        gr.Info(msg)
        return(session_state, gr.update(visible=True), gr.update(visible=False))

    
    session_state={"user_id": id, "c_ids": None}
    messages = load_messages(id)
    print(messages)
    return (session_state, 
            gr.update(visible=False), 
            gr.update(visible=True), 
            gr.update(value=messages),
            messages[0]
            )


with gr.Blocks(title="HestIA", fill_height=True, fill_width=True) as app:

    session_state = gr.State({"user_id": None, "c_ids": None})
    """
    TODO
    """
    with gr.Row():
        gr.Markdown("## itrust local AI - HestIA")
        #logout = gr.Button("Logout", icon="./assets/logout_icon.svg", size="sm", scale=1)
    """
    with gr.Row(visible=True) as login:
        gr.Column(scale=1)
        with gr.Column(scale=2):
            user = gr.Textbox(label="Username")
            pw = gr.Textbox(label="Password", type="password")

            login_btn = gr.Button("Log In", variant="primary")
        gr.Column(scale=1)"""


    with gr.Row(visible=True) as chatbox:
        with gr.Sidebar(position="right") as settings_panel:
            model = gr.Dropdown(choices=MODELS, label="Model", interactive=True)

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

            info = gr.Textbox(value="Your chat history is temporary. \
                              Conversations will be erased when you close the browser." ,label="Warning", )


        chatbot = gr.Chatbot(buttons=["copy"], 
                             height="calc(100vh - 200px)",
                             show_label=False)
        """
        with gr.Column(scale=1):
            new_chat = gr.Button("New Chat", variant="primary",)
        
            conv_list = gr.Dataset(components=[gr.Textbox(visible=False, show_label=False, interactive=True)],
                                    samples=[], show_label=False, layout="table")
        
        new_chat.click(fn=create_new_chat, inputs=[chatbot, session_state], outputs=[session_state, 
                                                                            conv_list,
                                                                            chatbot] )
        
        conv_list.click(fn=load_messages, inputs=[conv_list, session_state], outputs=chatbot)"""

        with gr.Column(scale=8):
            chat = gr.ChatInterface(
                fn=chat_interface,
                chatbot=chatbot,
                additional_inputs=[model, context, enable_rag, 
                                   collection, mode, retrieval_limit, score_threshold],
                autoscroll=False, 
                fill_height=True,
                save_history=True
                )
        #gr.on(triggers=chat.con, fn=print, inputs=[chat])
    

    """
    login_btn.click(
        fn=do_login,
        inputs=[user, pw, session_state],
        outputs=[session_state, 
                 login, 
                 chatbox, 
                 chat.saved_conversations, 
                 chatbot]
    )
    
    gr.on(triggers=[chat.saved_conversations.change], 
          fn=chat._save_conversation, 
          inputs=[chat.conversation_id, chatbot, chat.saved_conversations],
          outputs=[chat.conversation_id, chat.saved_conversations], trigger_mode="once")


    def print_chat():
        print(user_conversations)
        return gr.update(value=user_conversations), gr.update(value=user_conversations[0])
    gr.on(triggers=enable_rag.change, fn=print_chat, inputs=[], 
          outputs=[chat.saved_conversations, chat.chatbot])"""

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
            return handle_form_submission(*args[:5])
        else:
            return handle_form_submission(*args[-4:])
    
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