from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

QDRANT_URL = "http://localhost:6333"

client = QdrantClient(url=QDRANT_URL)

class VectorDBManager:

    def __init__(self, embedding_model, splitter):
        self.embedding_model = embedding_model
        self.splitter = splitter
        self.collections = None


    def initialize_collection(self):
        pass
    
    def update_collection(self):
        pass

    