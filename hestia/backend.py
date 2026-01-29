from abc import ABC
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, NamedVector
from typing import Optional, Dict, Any
import uuid
import requests
import os

import frontmatter
from pathlib import Path

from hestia.core import text_splitter as splitter

QDRANT_URL = "http://192.168.0.34:6333"
OLLAMA_URL = "http://192.168.0.34:11434"

DEFAULT_EMBEDDING_MODEL = "qwen3-embedding:0.6b"
DEFAULT_GEN_MODEL = "minstral-3:14b"
DEFAULT_TEXT_SPLITTER = "SectionSplitter"
DEFAULT_TAG_LIST = [
    "ISMS", "DocMgmt", "CoC", "Tech", "Org", "Phys"
]

DEFAULT_CONFIG = {
    "vectors":{
        "Default": {
            "size": 1024,
            "distance": "Cosine"
        }
    }
}

DEFAULT_RAG_CONFIG= {
    "vectors": {
        "Default": {
            "size": 1024,
            "distance": "Cosine"
        }, 
        "summary" : {
            "size": 1024,
            "distance": "Cosine"
        }, 
        "question" : {
            "size": 1024,
            "distance": "Cosine"
        } 
    },
    "sparse_vectors" : {
        "tags": {}
    }
}


class StorageBackend(ABC):

    def __init__(self):
        pass
    
    def initialize(self, collection_name):
        pass
    def store_chunk(self):
        pass

    def query(self):
        pass

class QdrantDBBackend(StorageBackend):

    def __init__(self):
        super().__init__()
        self.client = QdrantClient(url=QDRANT_URL)

    def initialize(self, collection_name: str, config: Optional[Dict[str, Any]] = DEFAULT_CONFIG) -> None:

        if not self.client.collection_exists(collection_name=collection_name):
            # replace with logging.info
            print(f"Collection '{collection_name}' not found → creating new collection.")
        
            vectors_config_dict = {}
            for vector_field, params in config["vectors"].items():
                vectors_config_dict[vector_field] = VectorParams(size=params["size"], distance=params["distance"])

            self.client.create_collection(
                collection_name=collection_name, 
                vectors_config=vectors_config_dict
            )

    def upsert(self, collection_name: str, points: Dict[str, Any]) -> None:
        
        for point in points:
            # unsafe like this, but what are the chances?
            point_id = str(uuid.uuid4())

            self.client.upsert(
                collection_name=collection_name,
                wait=True,
                points=[PointStruct(
                    id=point_id, vector=point["vectors"],
                    payload=point["payload"]
                )],
            )

    def delete_collection(self, collection_name: str) -> None:
        self.client.delete_collection(collection_name)

    def query(self, embedding: list[float], collection_name: str, **kwargs):
        query_result = self.client.query_points(collection_name, 
                                          query=embedding,
                                          using="content", 
                                          limit=1)

        return query_result

    def close(self):
        self.client.close()


class RAGManager:

    def __init__(self, storage_backend):
        self.storage_backend = storage_backend

    
    def convert(self, document):
        """
        Docstring for convert
        
        wrapper for Converter class.

        :param self: Description
        :param document: Description
        """
        pass

    def split(self, document, splitter=DEFAULT_TEXT_SPLITTER):
        """
        Docstring for split
        
        is document a md file(stream) or not. 
        if not call convert document
        
        with md file split document using a
        text-splitter.

        text-splitter returns List[Chunks]

        split function basically wrapper for text-splitter

        :param self: Description
        :param document: Description
        """
        pass

    def embed(self, data, model=DEFAULT_EMBEDDING_MODEL):
        """
        Generate embedding for data with model.

        :param self: Description
        :param data: Description
        """
        response = requests.post(
            f"{OLLAMA_URL}/api/embed",
            json={"model": model, "input": data},
        )
        if len(response.json()["embeddings"]) > 0:
            return response.json()["embeddings"][0]
        else:
            return None

    def generate_summary(self, data, model=DEFAULT_GEN_MODEL):

        url = f"{OLLAMA_URL}/api/generate"
        preface = "Generate a summary for the following:\n"
        payload = {
            "model": model,
            "prompt": preface + data,
        }
        response = requests.post(url, payload)

        return response.json()["response"]

    def generate_question(self, data, model=DEFAULT_GEN_MODEL):
        url = f"{OLLAMA_URL}/api/generate"
        preface = "Generate a representative question for the following:\n"
        payload = {
            "model": model,
            "prompt": preface + data,
        }
        response = requests.post(url, payload)

        return response.json()["response"]

    def generate_tags(self, data, model=DEFAULT_GEN_MODEL, tag_list=DEFAULT_TAG_LIST):
        url = f"{OLLAMA_URL}/api/generate"
        preface = "Generate appropriate tags for the following:\n"
        payload = {
            "model": model,
            "prompt": preface + data,
        }
        response = requests.post(url, payload)

        return response.json()["response"]

    def store_chunk(self, chunk, collection):
        """
        call when chunk is build and ready to be stored 
        in database/collection

        check if collection exists, if not call initialize
        collection
        :param self: Description
        :param chunk: Description
        """
        pass


def embed(data, model=DEFAULT_EMBEDDING_MODEL):
        """
        Generate embedding for data with model.

        :param self: Description
        :param data: Description
        """
        response = requests.post(
            f"{OLLAMA_URL}/api/embed",
            json={"model": model, "input": data},
        )
        if len(response.json()["embeddings"]) > 0:
            return response.json()["embeddings"][0]
        else:
            return None
        
def load(filepath):
    path = Path(filepath)

    if not path.exists():
        raise FileNotFoundError(f"Input file does not exist: {path}")

    if not path.is_file():
        raise ValueError(f"Input is not a file: {path}")

    try:
        with path.open(encoding="utf-8") as f:
            return frontmatter.load(f)
    except Exception as e:
        raise RuntimeError(
            f"Failed to load frontmatter from file: {path}"
        ) from e


if __name__ == "__main__":
    collection = "itrust ISMS"
    backend = QdrantDBBackend()
    
    backend.initialize(collection, config=DEFAULT_RAG_CONFIG)

    dirpath = "./dump"

    documents = [doc for doc in os.listdir(dirpath) if doc.endswith(".md")]
    print(f"Detected {len(documents)} files.")
    for doc_name in documents:
        filepath = os.path.join(dirpath, doc_name)
        print(f"Embedding file: {doc_name}")
        with open(filepath, "r", encoding="utf-8") as file:
            document = load(filepath)
            #meta = {**document.metadata, "source": doc_name}
            content = document.content

            chunks = splitter.SectionSplitter().split(document.content, source=document.metadata["source"])
            
            for chunk in chunks:
                vector = chunk.embed()
                payload = chunk.to_dict()

                if not vector:
                    continue

                point = [{
                    "vectors": {
                        "Default": vector
                    },
                    "payload": payload
                }]

                backend.upsert(collection, point)
    
    info = backend.client.get_collection(collection_name=collection)
    print(f"All documents embedded. {info.points_count} points created.")

    """query = "How to evaluate competence?"
    query_embed = embed(query)
    results = backend.query(embedding=query_embed, collection_name=collection)
    print(results)"""

    