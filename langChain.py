from langchain_community.document_loaders import PyPDFLoader
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import requests
import uuid
import datetime
import time

client = QdrantClient(url="http://localhost:6333")

if not client.collection_exists(collection_name="PDFembeddings"):
    client.create_collection(
        collection_name="PDFembeddings",
        vectors_config=VectorParams(size=1024, distance=Distance.COSINE),
    )

def write_to_file(filename, content, mode="w"):
    with open(filename, mode, encoding="utf-8") as f:
        f.write(content)

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
                collection_name="PDFembeddings",
                wait=True,
                points=[PointStruct(
                    id=chunk_id, vector=embeddings,
                    payload=adjusted_metadata
                )],
            )

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

def initialize_database(path):
    loader = PyPDFLoader("./docs/512_STA_ITR-Classification_v1.3.pdf")
    documents = loader.load() 

    for page in documents:
        content = page.page_content
        metadata = page.metadata

        store_article(metadata=metadata, chunks=[content])



def main():

    path = "./docs/"
    #initialize_database(path)

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
        collection_name="PDFembeddings",
        query=embeddings,
        with_payload=True,
        limit=5)
    t1_embed = time.perf_counter()
    
    relevant_passages = "\n".join(
        [f"- Article Title: {point.payload['title']} - {point.payload['subject']} -- page: {point.payload['page_label']} -- Article Content: {point.payload['content']}" for point in results.points])
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
    main()