import os
import json
import gradio as gr
from threading import Lock
from datetime import datetime

from typing import Dict,Any, Iterator
from hestia.settings import Settings
from hestia.utils import HttpClient

MODELS = Settings.WHITELIST_MODELS
CONTEXT_SIZE = Settings.DEFAULT_CONTEXT_SIZE
CSS_FILE = Settings.CSS_FILE
APP_DATA = Settings.APP_DATA
REQ_FILE = Settings.REQ_FILE
REQUEST_TIMEOUT = Settings.REQUEST_TIMEOUT
APP_URL = Settings.API_URL

VERSION = Settings.VERSION

Message = Dict[str, str] # {"role": "user"|"assistant"|"system", "content": "..."}

_lock = Lock()

http_client = HttpClient(base_url="http://127.0.0.1:7860")

def create_version_textbox(version=VERSION):
    html = f"""
    <style>
        .bottom-version-container {{
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            padding: 10px;
            background: #f0f0f0;
            text-align: center;
            font-family: Arial, sans-serif;
            font-size: 12px;
            z-index: 100;
            border-top: 1px solid #ddd;
        }}
    </style>
    <div class="bottom-version-container">
        {version}
    </div>
    """
    return html

def store_submission(form: dict):
    os.makedirs(APP_DATA, exist_ok=True)
    line = json.dumps(form, ensure_ascii=False)
    with _lock:
        with open(REQ_FILE, "a", encoding="utf-8") as f:
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
    gr.Info("✅ Thanks for your submission! We've received your feedback.", duration=3)

def stream(
        endpoint: str,
        payload: Dict[str, Any], #messages: List[Message], 
        options: Dict[str, Any] = None, 
        timeout=REQUEST_TIMEOUT
        ) -> Iterator[str]:

    partial = ""
    with http_client.post(endpoint, payload=payload, stream=True) as r:
        for chunk in r.iter_content(chunk_size=None):
            if not chunk:
                continue
            text = chunk.decode("utf-8", errors="ignore")
            if not text:
                continue
            partial += text
            yield partial


def chat_interface(message, history, model, context, 
                   enable_rag, collection, retrieval_limit, score_threshold
                ) -> Iterator:
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
        payload = {
        "message": message,
        "collection": collection,
        "stream": True,
        }
        yield from stream(endpoint="/api/rag", payload=payload)
    else:
        messages.append({"role": "user", "content": message})
        options = {"num_ctx": context}
        payload = {
        "messages": messages,
        "model": model,
        "options": options,
        "stream": True,
        }

        
        # Stream tokens to the UI
        yield from stream(endpoint="/api/chat", payload=payload)


def create_gui(api):
    with gr.Blocks(title="HestIA", fill_height=True, fill_width=True) as gradio_app:


        with gr.Row():
            gr.Markdown("## itrust local AI - HestIA")

        with gr.Row(visible=True) as chatbox:
            with gr.Sidebar(position="right") as settings_panel:
                model = gr.Dropdown(choices=MODELS, label="Model", interactive=True)

                context = gr.Slider(4096, 8 * 4096, value=CONTEXT_SIZE, step=4096,
                                    interactive=True, label="Context window",
                                    visible=False)
                
                with gr.Row():
                    enable_rag = gr.Checkbox(label="RAG", value=False)

                with gr.Group(visible=False) as rag_settings:
                    collection = gr.Dropdown(choices=["ITR ISMS"], 
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

                
                version = gr.HTML(create_version_textbox())

            chatbot = gr.Chatbot(buttons=["copy"], 
                                height="calc(100vh - 200px)",
                                show_label=False)

            with gr.Column(scale=8):
                chat = gr.ChatInterface(
                    fn=chat_interface,
                    chatbot=chatbot,
                    additional_inputs=[model, context, enable_rag, 
                                    collection, retrieval_limit, score_threshold],
                    autoscroll=False, 
                    fill_height=True,
                    save_history=True
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


    app = gr.mount_gradio_app(api, gradio_app, path="/home", 
                            theme=gr.themes.Soft(primary_hue="red", secondary_hue="pink", font="Corbel"),
                            css_paths=CSS_FILE,)
    
    
    return app