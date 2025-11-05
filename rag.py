from fastapi import FastAPI, Request
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import requests
import uuid
import argparse
import os
import datetime
import time
import frontmatter
import uvicorn


QDRANT_URL = "http://localhost:6333"
OLLAMA_URL = "http://localhost:11434"
DEFAULT_MODEL_EMBED = "mxbai-embed-large"
DEFAULT_MODEL_GENERATE = "llama3.1:8b"

client = QdrantClient(url=QDRANT_URL)

app = FastAPI()


def write_to_file(filename, content, mode="w"):
    with open(filename, mode, encoding="utf-8") as f:
        f.write(content)


def generate_embeddings(data: str, model=DEFAULT_MODEL_EMBED):
    
    response = requests.post(
        f"{OLLAMA_URL}/api/embed",
        json={"model": model, "input": data},
    )
    if len(response.json()["embeddings"]) > 0:
        return response.json()["embeddings"][0]
    else:
        return None

def create_chunks(article_content: str):
    chunks = []
    current_chunk = ""

    for line in article_content.split("\n\n"):
        if line.startswith("#"):
            chunks.append(current_chunk)
            current_chunk = line + "\n"
        else:
            current_chunk += line + "\n"

    return chunks

def store_document_chunks(chunks: list, metadata: dict, collection: str, model=DEFAULT_MODEL_EMBED):

    for chunk in chunks:
        # Generate a unique ID for each chunk
        chunk_id = str(uuid.uuid4())
        adjusted_metadata = {
            **metadata,
            "content": chunk
        }

        embeddings = generate_embeddings(chunk, model=model)

        if embeddings is not None:
            client.upsert(
                collection_name=collection,
                wait=True,
                points=[PointStruct(
                    id=chunk_id, vector=embeddings,
                    payload=adjusted_metadata
                )],
            )


def initialize_collection(dirpath: str, collection: str, model=DEFAULT_MODEL_EMBED, update=False):

    # check if exists and create if not.
    col_exists = client.collection_exists(collection_name=collection)
    if not col_exists:
        print(f"Collection '{collection}' not found → creating new collection.")
        client.create_collection(
            collection_name=collection,
            vectors_config=VectorParams(size=1024, distance=Distance.COSINE),
        )
    
        # get list of documents (filenames)
        documents = [doc for doc in os.listdir(dirpath) if doc.endswith(".md")]
        print(f"Detected {len(documents)} files.")
        for doc_name in documents:
            filepath = os.path.join(dirpath, doc_name)
            print(f"Embedding file: {doc_name}")
            with open(filepath, "r", encoding="utf-8") as file:
                document = frontmatter.load(file)
                meta = {**document.metadata, "source": doc_name}
                content = document.content

                chunks = create_chunks(content)
                
                store_document_chunks(chunks, meta, collection, model)
        
        info = client.get_collection(collection_name=collection)
        print(f"All documents embedded. {info.points_count} points created.")
        return {"total_files":len(documents), "points":info.points_count}    
    else:
        print("Collection already initialized. Nothing to do.")


def get_response(prompt, model=DEFAULT_MODEL_GENERATE):

    response = requests.post(
        f"{OLLAMA_URL}/api/generate",
        json={"model": model, "prompt": prompt, "stream": False}
    )

    return response.json()["response"]

def generate_augmented_prompt(prompt, context):
    
    relevant_articles = []
    for article in context.points:
        payload = article.payload

        title = payload.get("title", "Untitled Document")
        subtitle = payload.get("subtitle", "")
        short_title = payload.get("shortTitle", "")
        reference = payload.get("info", {}).get("reference", "")
        source = payload.get("source")
        content = payload.get("content")

        # Structure each retrieved item clearly for the LLM
        article_text = f"""
        [SOURCE: {source}]
        Title: {title}
        Subtitle: {subtitle}
        Reference: {reference}
        ShortTitle: {short_title}
        Content: {content}
        """
        relevant_articles.append(article_text.strip())

    relevant_articles_str = "\n\n".join(relevant_articles)

    augmented_prompt = f"""
    You are an assistant with access to a knowledge base of Markdown documents. Below are the most relevant excerpts retrieved from that database.
    <retrieved-data>
    {relevant_articles_str}
    </retrieved-data>
    Instruction:
    Using only the retrieved data above, answer the user's question. At the end of your answer, include a "Sources" section listing which [SOURCE] tags you actually used to generate your answer.
    <user-prompt>
    {prompt}
    </user-prompt>
    """

    return augmented_prompt

def RAG(prompt, collection, model=DEFAULT_MODEL_EMBED):

    # adjust for qdrant to handle properly
    adjusted_prompt = f"Represent this sentence for searching relevant passages: {prompt}"
    embedding = generate_embeddings(adjusted_prompt, model=model)

    results = client.query_points(collection_name=collection, 
                                  query=embedding,
                                  with_payload=True,
                                  limit=3)
    return results


@app.post("/init")
async def init_endpoint(request: Request):

    # initilaize qdrant collection
    body = await request.json()
    dirpath = body.get("dirpath", "./docs")
    collection = body.get("collection")
    result = initialize_collection(dirpath, collection) 
    return {"status": "completed", "details": result}

@app.post("/rag")
async def rag_endpoint(request: Request):

    model_embed = "mxbai-embed-large"


    current = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    body = await request.json()
    prompt = body.get("prompt")
    model_gen = body.get("model")
    collection = body.get("collection")
    
    t0 = time.perf_counter()
    context = RAG(prompt, collection, model_embed)
    augmented_prompt = generate_augmented_prompt(prompt, context)
    
    response = get_response(augmented_prompt, model_gen)
    t1 = time.perf_counter()

    t = t1 - t0
    write_to_file(f"./tests/{current}.md", augmented_prompt)
    write_to_file(f"./tests/{current}.md", "\n" + f"{response}", mode = "a")
    write_to_file(f"./tests/{current}.md", "\n Total:\t" + f"{t}", mode = "a")

    #print(response)
    return {"response": response}

if __name__ == "__main__":
    
    uvicorn.run(app, host="0.0.0.0", port=8099)