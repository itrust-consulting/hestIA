from abc import ABC, abstractmethod
from pathlib import Path
import frontmatter
import re
import json
import requests
import torch


from fastapi import FastAPI, Request
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import uuid
import os

_HEADING_RE = re.compile(r"^(#{1,5})\s+(.*)$")

DEFAULT_EMBEDDING_MODEL = "qwen3-embedding:0.6b"
DEFAULT_OUTPUT_DIR = "./dump/textsplitter/"
OLLAMA_URL = "http://localhost:11434"
QDRANT_URL = "http://localhost:6333"

client = QdrantClient(url=QDRANT_URL)


class Chunk():

    def __init__(self, content, metadata):
        self.content = content
        self.metadata = metadata
        self.parent = None
        self.summary = None
        self.question = None
        self.relations = None
        self.tags = None
        self.embedding = None

    def __str__(self):
        return self.content
    
    def __repr__(self):
        return f"text = {self.content}\nmetadata = {self.metadata}\nparent = {self.parent}\nsummary = {self.summary}\nquestion = {self.question}"
    
    def set_parent(self, parent_chunk):
        self.parent = parent_chunk

    def add_relation(self, chunk):
        self.relations.append(chunk)
    
    def to_dict(self):
        return {
            'content': self.content,
            'metadata': self.metadata,
            'summary': self.summary,
            'question': self.question,
            'parent_chunk': self.parent,
            'relations': self.relations
        }
    
    @classmethod
    def from_dict(cls, data):
        return cls()

    def embed(self, embedding_model=DEFAULT_EMBEDDING_MODEL):
        """
        Generate embedding for the content using a specified model.
        
        :param self: Description
        :param embedding_model: Description
        """
        if self.content is None:
            raise ValueError("Chunk is empty. Nothing to embed.")
        
        response = requests.post(
            f"{OLLAMA_URL}/api/embed",
            json={"model": embedding_model, "input": self.content},
        )
        if len(response.json()["embeddings"]) > 0:
            return response.json()["embeddings"][0]
        else:
            return None

class BaseSplitter(ABC):

    def __init__(self):
        self._chunks = None
        
    @property
    def chunks(self):
        """List of Chunk objects resulting from the split operation."""
        return self._chunks
        
    @abstractmethod
    def split(self, text, metadata = None):
        """
        Abstract method that must be implemented by subclasses.
        
        This method should contain the logic for splitting the document into Chunks
        and store the result in self._chunks.
        """
        pass

    def serialize(self):

        if self._chunks is None:
            return []
        
        chunks_dict = []
        for chunk in self._chunks:
            chunk_dict = chunk.to_dict()
            chunks_dict.append(chunk_dict)
        
        return chunks_dict

    def reset(self):
        """Resets the chunks list to its initial empty state."""
        self._chunks = None

    def dump(self, output_dir=DEFAULT_OUTPUT_DIR):
        
        dir = Path(output_dir)
        dir.mkdir(parents=True, exist_ok=True)

        chunks = self.serialize()

        filepath = dir / "tmp.json"
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(chunks, f, indent=4)


class FixedSizeSplitter(BaseSplitter):
    """
    FixedSizeSplitter splits document into chunks of fixed token length.
    
    :var TODO: Description
    """
    def __init__(self, chunk_size = 500):
        super().__init__()
        self.chunk_size = chunk_size

    def split(self, text, metadata = None):
        
        chunks = []
        text_length = len(text)

        num_chunks = (text_length // self.chunk_size) + 1

        for i in range(num_chunks):
            start = i * self.chunk_size
            end = (i + 1) * self.chunk_size
            chunk_text = text[start:end].strip()
            
            if not chunk_text:
                continue  # Skip empty chunks
            
            chunk_meta = {"position": i}
            chunk = Chunk(content = chunk_text, metadata = chunk_meta)
            chunks.append(chunk)

        self._chunks = chunks
        return chunks


class SlidingWindowSplitter(BaseSplitter):

    def __init__(self, chunk_size = 500, overlap = 50):
        super().__init__()
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.stride = chunk_size - overlap

    def split(self, text, metadata=None):
        """
        Splits the input text into overlapping chunks using a sliding window approach.
        
        Args:
            text (str): The input text to be split.
            metadata (dict, optional): Additional metadata associated with the chunks. Defaults to None.
            
        Returns:
            list: A list of Chunk objects, each containing a portion of the text with associated metadata.
        """
        text_length = len(text)
        num_chunks = ((text_length - self.chunk_size) // self.stride) + 1
        
        chunks = []
        for i in range(num_chunks):
            start = i * self.stride
            end = start + self.chunk_size
            chunk_text = text[start:end].strip()
            chunk_meta = {"position": i}
            chunk = Chunk(content=chunk_text, metadata=chunk_meta)
            chunks.append(chunk)

        # Handle remaining text if any (when text length is not perfectly divisible by stride)
        remainder_start = num_chunks * self.stride
        if remainder_start < text_length:
            chunk_text = text[remainder_start:].strip()
            chunk = Chunk(content=chunk_text, metadata=metadata)
            chunks.append(chunk)

        self._chunks = chunks
        
        return chunks


class SentenceSplitter(BaseSplitter):

    def __init__(self):
        super().__init__()

    def split(self, text, metadata = None):
        try:
            import spacy
            nlp = spacy.load("en_core_web_sm")
            nlp.enable_pipe("senter")
        except ModuleNotFoundError:
            raise ImportError(
                    "spaCy is not installed. Please install it with:\n"
                    "pip install spacy"
                )

        doc = nlp(text)

        chunks = []
        for i, sentence in enumerate(doc.sents):
            if sentence:
                chunk_text = sentence.text.strip()
                chunk_meta = {"position": i}
                chunk = Chunk(content = chunk_text , metadata = chunk_meta)
                chunks.append(chunk)

        self._chunks = chunks

        return chunks


class SectionSplitter(BaseSplitter):

    def __init__(self, max_depth = 5):
        super().__init__()
        self._max_depth = max_depth 

    def split(self, text, metadata = None):
        """
        TODO:
        - parent chunks
        - load into Chunk
        
        :param self: Description
        :param max_level: Description
        """
        if not 1 <= self._max_depth <= 6:
            raise ValueError("max_level must be between 1 and 5")

        lines = text.splitlines()
        sections = []
        current_section = None

        for i, line in enumerate(lines):
            m = _HEADING_RE.match(line)
            if not m:
                if current_section is not None:
                    current_section["content"].append(line.strip())
                continue

            level = len(m.group(1))
            title = m.group(2).strip()

            # Ignore headings deeper than max_level for splitting
            if level > self._max_depth:
                continue
            
            current_section = {
                "title": title,
                "level": level,
                "content": [],
                "position": i,
            }

            if current_section is not None:
                sections.append(current_section)

        chunks = []
        for section in sections:
            chunk_text = '\n'.join(section["content"])
            chunk_meta = {
                "title": section["title"],
                "level": section["level"],
                "position": section["position"],
            }

            chunk = Chunk(content = chunk_text, metadata = chunk_meta)
            chunks.append(chunk)

        self._chunks = chunks

        return chunks

    
class SemanticSplitter(BaseSplitter):

    def __init__(self, window_size = 4, stride = 1, threshold = 0.75, hysteresis = 1):
        """
        Sliding-window semantic splitter.
        
        :param self: Description
        :param window_size: Number of sentences in each window.Must be even number.
        :param stride: Number of sentences to move the window forward each step.
        :param threshold: Similarity threshold. Text is split if similarity < threshold.
        :param hysteresis: Number of consecutive windows below threshold required to trigger a split. 
                           Increas number to avoid over-segmentation.
        """
        super().__init__()
        if window_size < 2:
            raise ValueError("window_size must be >= 2")
        if stride < 1:
            raise ValueError("stride must be >= 1")
        if not (0.0 <= threshold <= 1.0):
            raise ValueError("threshold should be in [0, 1] for cosine similarity")

        if window_size % 2 != 0:
            raise ValueError("window_size should be even for equal-halves similarity comparison.")

        self._window_size = window_size
        self._stride = stride
        self._threshold = threshold
        self._hysteresis = hysteresis
        self._nlp = None

    def _lazy_load_dependencies(self):
        
        if self._nlp is not None:
            return
        try:
            import spacy
            self._nlp = spacy.load("en_core_web_sm")
            self._nlp.enable_pipe("senter")
        except ModuleNotFoundError as e:
            raise ImportError(
                "spaCy is not installed. Please install it with:\n"
                "  pip install -U spacy\npython -m spacy download en_core_web_sm."
            ) from e

        
    def _get_embedding(self, text, embedding_model=DEFAULT_EMBEDDING_MODEL, timeout = 30):
        
        response = requests.post(
            f"{OLLAMA_URL}/api/embed",
            json={"model": embedding_model, "input": text},
            timeout=timeout
        )
        if len(response.json()["embeddings"]) > 0:
            return response.json()["embeddings"][0]
        else:
            return None
    
    def _calculate_similarity(self, embed1, embed2):

        tens1 = torch.tensor(embed1)
        tens2 = torch.tensor(embed2)
        cos = torch.nn.CosineSimilarity(dim=0)
        return cos(tens1.squeeze(), tens2.squeeze()).item()
        
    def split(self, text, metadata=None):
        """
        SemanticSplitter based on Sliding Window principle and Sentence splitter.

        :param self: Description
        :param text: Description
        :param metadata: Description
        """
        self._lazy_load_dependencies()
        # Split document into sentences.
        doc = self._nlp(text)
        sentences = [sent.text.strip() for sent in doc.sents if sent.text.strip()]

        window_size = self._window_size  # Define the window size as four sentences
        if len(sentences) < window_size:
            # Not enough sentences to form a window; return as single chunk
            chunk = Chunk(content=" ".join(sentences), metadata=metadata)
            self._chunks = [chunk]
            return [chunk]

        # prepare sliding window parameter
        k = self._window_size // 2
        chunks = []
        current_chunk_start = 0
        below_streak = 0 # consecutive windows below threshold
        half_pair_cache = {}
        
        def embed_range(start, end):
            key = (start, end)
            if key in half_pair_cache:
                return half_pair_cache[key]
            block = " ".join(sentences[start:end])
            emb = self._get_embedding(block)
            half_pair_cache[key] = emb
            return emb

        # Slide window with the configured stride
        # valid i: 0 .. len(sentences) - window_size
        for i in range(0, len(sentences) - self._window_size + 1, self._stride):
            first_start, first_end = i, i + k
            second_start, second_end = i + k, i + 2 * k

            emb_first = embed_range(first_start, first_end)
            emb_second = embed_range(second_start, second_end)
            similarity = self._calculate_similarity(emb_first, emb_second)

            # If similarity could not be computed, treat as "no decision" (i.e., don't split here).
            if similarity is None:
                below_streak = 0
                continue

            if similarity < self._threshold:
                below_streak += 1
            else:
                below_streak = 0


            if below_streak >= self._hysteresis:
                # Split boundary between the halves: after the (i + k - 1)-th sentence.
                split_after_idx = i + k - 1
                if split_after_idx >= current_chunk_start:
                    chunk_content = " ".join(sentences[current_chunk_start:split_after_idx + 1])
                    if chunk_content:
                        chunks.append(Chunk(content=chunk_content, metadata=metadata))
                current_chunk_start = split_after_idx + 1
                below_streak = 0

        # Tail chunk
        if current_chunk_start < len(sentences):
            tail_content = " ".join(sentences[current_chunk_start:])
            if tail_content:
                chunks.append(Chunk(content=tail_content, metadata=metadata))

        self._chunks = chunks
        return chunks


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
    

def store_document_chunks(chunks, collection, embedding_model=DEFAULT_EMBEDDING_MODEL):

    for chunk in chunks:
        # Generate a unique ID for each chunk
        chunk_id = str(uuid.uuid4())
        adjusted_metadata = {
            **chunk.metadata,
            "content": chunk.content
        }

        embeddings = chunk.embed(embedding_model=embedding_model)

        if embeddings is not None:
            client.upsert(
                collection_name=collection,
                wait=True,
                points=[PointStruct(
                    id=chunk_id, vector=embeddings,
                    payload=adjusted_metadata
                )],
            )

def initialize_collection(dirpath: str, collection: str, model=DEFAULT_EMBEDDING_MODEL, update=False):

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
                #meta = {**document.metadata, "source": doc_name}
                content = document.content

                splitter = FixedSizeSplitter()
                chunks = splitter.split(content)
                
                store_document_chunks(chunks, collection, model)
        
        info = client.get_collection(collection_name=collection)
        print(f"All documents embedded. {info.points_count} points created.")
        return {"total_files":len(documents), "points":info.points_count}    
    else:
        print("Collection already initialized. Nothing to do.")



if __name__ == "__main__":
    """filepath = "D:/hfries/Desktop/Projects/ITR-LLM/A_Initiation/A1_Prototypes/dump/1_POL_ITR-ISMS_v2.0.md"
    
    file = load(filepath)
    text = file.content
    metadata = file.metadata

    splitter = SemanticSplitter(hysteresis=2)
    chunks = splitter.split(text)
    splitter.dump()"""
    input_path = "./dump"
    initialize_collection(input_path, "FixedSizeSplitter")


    
