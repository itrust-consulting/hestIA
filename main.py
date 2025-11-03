#from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import requests
import uuid
import argparse
import os
import datetime
import time

client = QdrantClient(url="http://localhost:6333")

def write_to_file(filename, content, mode="w"):
    with open(filename, mode, encoding="utf-8") as f:
        f.write(content)


# Chunked in paragraphs.
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


def generate_response(prompt: str):
    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": "llama3.1:8b",
            "prompt": prompt,
            "stream": False,
        }
    )
    return response.json()["response"]


def generate_embeddings(text: str):
    response = requests.post(
        "http://localhost:11434/api/embed",
        json={"model": "mxbai-embed-large", "input": text},
    )
    if len(response.json()["embeddings"]) > 0:
        return response.json()["embeddings"][0]
    else:
        return None


def store_article(metadata: dict, chunks: list[str]):
    for chunk in chunks:
        # Generate a unique ID for each chunk
        chunk_id = str(uuid.uuid4())
        adjusted_metadata = {
            **metadata,
            "content": chunk
        }
        embeddings = generate_embeddings(chunk)

        if embeddings is not None:
            client.upsert(
                collection_name="articles",
                wait=True,
                points=[PointStruct(
                    id=chunk_id, vector=embeddings,
                    payload=adjusted_metadata
                )],
            )

def get_file_content(path):
    with open(path, "r") as file:
        content = file.read()
    return content

def initialize_database(path):

    if not client.collection_exists(collection_name="articles"):
        client.create_collection(
            collection_name="articles",
            vectors_config=VectorParams(size=1024, distance=Distance.COSINE),
        )

        documents = [doc for doc in os.listdir(path) if doc.endswith(".md")]
        for doc in documents:
            metadata = {}
            file_path = os.path.join(path, doc)
            content = get_file_content(file_path)
            chunks = create_chunks(content)
            metadata["slug"] = doc.replace(".md", "")
            store_article(metadata=metadata, chunks=chunks)

    return 0

def main():

    path = "./docs/"
    initialize_database(path)

    print("Database initialized. How can I help you with?")
    prompt = input("")
    adjusted_prompt = f"Represent this sentence for searching relevant passages: {prompt}"
    
    t0_embed = time.perf_counter()
    response = requests.post(
        "http://localhost:11434/api/embed",
        json={"model": "mxbai-embed-large", "input":adjusted_prompt},
    )
    data = response.json()
    embeddings = data["embeddings"][0]

    results = client.query_points(
        collection_name="articles",
        query=embeddings,
        with_payload=True,
        limit=10)
    t1_embed = time.perf_counter()
    
    relevant_passages = "\n".join(
        [f"- Article Title: -- Article Slug: {point.payload['slug']} -- Article Content: {point.payload['content']}" for point in results.points])
    augmented_prompt = f"""
      The following are relevant passages:
      <retrieved-data>
      {relevant_passages}
      </retrieved-data>

      Here's the original user prompt, answer with help of the retrieved passages:
      <user-prompt>
      {prompt}
      </user-prompt>
    """

    current = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    write_to_file(f"./tests/{current}.md", augmented_prompt)
    
    t0_request = time.perf_counter()
    response = generate_response(augmented_prompt)
    t1_request = time.perf_counter()


    
    t_embed = t1_embed - t0_embed
    t_generate = t1_request - t0_request
    t_tot = t_embed + t_generate
    print(response, f"\t Total time: {t_embed} + {t_generate} = {t_tot}s")
    
    write_to_file(f"./tests/{current}.md", "\n" + f"{response}", mode = "a")
    write_to_file(f"./tests/{current}.md", "\n Time to embed and retrieve data:\t" + f"{t_embed}", mode = "a")
    write_to_file(f"./tests/{current}.md", "\n Time to generate response:\t" + f"{t_generate}", mode = "a")
    write_to_file(f"./tests/{current}.md", "\n Total:\t" + f"{t_tot}", mode = "a")
    

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="itrust LLM - Test.")
    # initialize database: path to root, [opt] output path, [opt] ignore rules
    #parser.add_argument("--init", required=True,
    #                    help="Initialize database.")
    # to run in CLI or spawn gui
    args = parser.parse_args()
    
    
    main()

    