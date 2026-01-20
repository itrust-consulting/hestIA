import gradio as gr
import requests

# --- Configuration ---
RAG_URL = "http://localhost:8099/rag"
OLLAMA_URL = "http://localhost:11434"
DEFAULT_MODEL = "llama3.2:3b"

# --- Core logic ---
def generate(prompt, model, use_rag=False, collection=None):
    """
    If RAG is enabled, forwards prompt to the RAG backend.
    Otherwise, queries the base model directly.
    """
    if use_rag:
        print(f"[RAG MODE] -> Sending prompt to {RAG_URL} using model={model}, collection={collection}")
        try:
            response = requests.post(
                RAG_URL,
                json={"prompt": prompt, "model": model, "collection": collection},
            )
            response.raise_for_status()
            return response.json().get("response", "No response from RAG service.")
        except Exception as e:
            return f"[RAG ERROR] {e}"
    else:
        print(f"[LLM MODE] -> generating response locally via Ollama.")
        try:
            response = requests.post(
                f"{OLLAMA_URL}/api/generate",
                json={"model": model, "prompt": prompt, "stream": False},
            )
            response.raise_for_status()
            return response.json().get("response", "No response from LLM.")
        except Exception as e:
            return f"[LLM ERROR] {e}"

# --- Gradio Interface ---
def chat_interface(message, history, use_rag, model, collection):
    """
    Gradio ChatInterface callback.
    Handles message submission and RAG toggle.
    """
    reply = generate(message, model=model, use_rag=use_rag, collection=collection)
    return reply


# --- UI Elements ---
with gr.Blocks(title="RAG + LLM Chat Demo") as demo:
    gr.Markdown("## Local LLM + RAG Chat Demo")
    gr.Markdown(
        "Toggle between normal LLM chat and RAG"
    )

    with gr.Row():
        use_rag = gr.Checkbox(label="Use RAG", value=False)
        model = gr.Dropdown(
            choices = ["llama3.2:3b", "llama3.1:8b"],
            label="Select Model",
            interactive=True
        )
        collection = gr.Dropdown(
            choices = ["PoC-Datastore", "PoC-Datastore-1"],
            label="Select Collection",
            interactive=True
        )

    chat = gr.ChatInterface(
        fn=chat_interface,
        additional_inputs=[use_rag, model, collection],
        title="Local AI Chat",
        description="Chat normally or enable RAG for retrieval-augmented responses.",
    )

demo.launch(server_name="127.0.0.1", server_port=7860)
