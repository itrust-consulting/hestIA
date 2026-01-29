
import os
import json
import re
import requests
import gradio as gr
from qdrant_client import QdrantClient

# ---- Config ----
DEFAULT_CONTEXT_SIZE = 8192  # set to your DEFAULT_CONTEXT_SIZE
REQUEST_TIMEOUT = (10, 180)  # (connect, read)
# --- Configuration ---
DEFAULT_QDRANT_URL = "http://qdrant:6333"  # Docker Compose service name
DEFAULT_OLLAMA_URL = "http://ollama:11434"

QDRANT_URL = os.getenv("QDRANT_BASE_URL", DEFAULT_QDRANT_URL)
OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", DEFAULT_OLLAMA_URL)

DEFAULT_MODELS = ["ministral-3:14b", "deepseek-r1:32b"]
DEFAULT_EMBEDDING_MODEL = "qwen3-embedding:0.6b"
DEFAULT_CONTEXT_SIZE = 8192

EMBED_RE = re.compile(r"(?:^|[-_:])embed(?:$|[-_:])|embedding|nomic-embed|mxbai-embed|all-minilm|bge-|e5-",
                      re.IGNORECASE)

client = QdrantClient(url=QDRANT_URL)

# ---- RAG-Pipeline START ----

def embed(data, model=DEFAULT_EMBEDDING_MODEL):
    response = requests.post(
        f"{OLLAMA_URL}/api/embed",
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
    adjusted_prompt = f"Represent this sentence for searching relevant passages: {prompt}"
    embedding = embed(adjusted_prompt, model=model)

    results = client.query_points(collection_name=collection, 
                                  query=embedding,
                                  using="Default",
                                  with_payload=True,
                                  limit=limit)
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
        resp = client.get_collections()
        return [c.name for c in resp.collections]
    except Exception as e:
        print(f"[DB ERROR] {e}")
        return []

def get_ollama_models(filter_embeddings=True):
    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=10)
        r.raise_for_status()
        data = r.json()
        models = [m["name"] for m in data.get("models", [])]
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
    url = f"{OLLAMA_URL}/api/chat"
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

def chat_interface(message, history, model, context, enable_rag, collection, retrieval_limit):
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
        retrieved_data = query(message, collection=collection, limit=retrieval_limit)
        formatted_data = format_retrieved_data(retrieved_data)
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

with gr.Blocks(title="HestIA") as app:
    gr.Markdown("## itrust local AI - HestIA")

    
    with gr.Row():
        with gr.Column(scale=1, visible=True) as settings_panel:
            
            with gr.Row():
                gr.Markdown("### Model Settings")
            
            model = gr.Dropdown(choices=DEFAULT_MODELS, label="Select Model", interactive=True)
            context = gr.Slider(4096, 8 * 4096, value=DEFAULT_CONTEXT_SIZE, step=4096,
                                interactive=True, label="Context window")

            with gr.Row(visible=False):
                btn_models = gr.Button("Refresh models")
                btn_db = gr.Button("Refresh databases")

            gr.Markdown("### Toggle Features and Tools")
            
            with gr.Group(visible=True) as rag_settings:
                enable_rag = gr.Checkbox(label="RAG", value=False, )
                collection = gr.Dropdown(choices=["itrust ISMS"], label="Select Database", interactive=True)
                retrieval_limit = gr.Number(value=5, precision=0, 
                                                label="Retrieval limit (top-k)",
                                                interactive=True, 
                                                maximum=10)

            #enable_search = gr.Checkbox(label="Web search (not in demo)", value=False)

            btn_models.click(fn=refresh_models, inputs=None, outputs=model)
            btn_db.click(fn=refresh_collections, inputs=None, outputs=collection)

        with gr.Column(scale=3):
            chat = gr.ChatInterface(
                fn=chat_interface,
                chatbot=gr.Chatbot(buttons=["copy"]),
                additional_inputs=[model, context, enable_rag, collection, retrieval_limit],
                autoscroll=False, 
                fill_height=True
            )

    
    # Load initial choices on startup
    #app.load(fn=refresh_models, inputs=None, outputs=model)
    #app.load(fn=refresh_collections, inputs=None, outputs=collection)

    
if __name__=="__main__":
    app.launch(theme=gr.themes.Soft(primary_hue="red", secondary_hue="pink", font="Corbel"),
               height="100%", width="100%",
               server_name="0.0.0.0", server_port=7860)