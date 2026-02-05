import os
import pathlib


# --- Settings ---
PROJECT_ROOT_PATH = pathlib.Path(os.path.abspath(os.path.join(__file__, ".."))).parent.absolute()
print(PROJECT_ROOT_PATH)
# --- Logging --- 
APP_DATA = PROJECT_ROOT_PATH.joinpath("./app/data/")
LOG_FILE = PROJECT_ROOT_PATH.joinpath("./log.log")
REQ_FILE = PROJECT_ROOT_PATH.joinpath("./requests.json")
CSS_FILE = PROJECT_ROOT_PATH.joinpath("./assets/styles.css")


verbosity = 0  # global verbosity setting for controlling string formatting
PRINT_VERBOSITY = 0  # minimum verbosity to using `print`
STR_VERBOSITY = 3  # minimum verbosity to use verbose `__str__`
MAX_VERBOSITY = 4

LOG_LEVEL = MAX_VERBOSITY

# --- HTTP ---
REQUEST_TIMEOUT = (10.0, 180.0)

# --- DB Settings ---
DEFAULT_DB_URL = "http://192.168.0.34:6333"  # change to http://qdrant:6333 in docker deployment
DB_URL = os.getenv("QDRANT_BASE_URL", DEFAULT_DB_URL)

DEFAULT_DB_SETTINGS = {
    "vectors": {
        "name": "Default",
        "size": 1024,
        "distance": "Cosine"
        },
        "sparse_vectors": {},
    }
DEFAULT_QUERY_OPTIONS = {
            "using": "Default",
            "limit": 5,
            "offset": 0,
            "score_threshold": 0.2,
            "with_payload": True,
            "with_vectors": False,
            "filter": None
            }

# --- LLM Settings ---
DEFAULT_LLM_URL = "http://192.168.0.34:11434" # change to http://ollama:11434 in docker deployment
LLM_URL = os.getenv("OLLAMA_BASE_URL", DEFAULT_LLM_URL)

DEFAULT_CONTEXT_SIZE = 32768
DEFAULT_MODELS = ["ministral-3:14b", "deepseek-r1:32b"]
DEFAULT_GEN_MODEL = "ministral-3:14b"
DEFAULT_EMB_MODEL = "qwen3-embedding:0.6b"
DEFAULT_RRK_MODEL = "dengcao/Qwen3-Reranker-4B:Q8_0"

DEFAULT_LLM_SETTINGS = {
        "gen": {"model": DEFAULT_GEN_MODEL, },
        "emb": {"model": DEFAULT_EMB_MODEL, "vector_size": 1024},
        "rrk": {"model": DEFAULT_RRK_MODEL, "temperature": 0, "num_predict": 3, "raw": True},
        }
## --- RAG Settings ---

### --- Parser + Splitter
DUMP_DIR = "./dump"
SUPPPORTED_EXTENSIONS = [".docx", ".pdf"]
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

### --- Query ---


DEFAULT_EXECUTION_CONTEXT = {
    "llm": {
        "model": DEFAULT_GEN_MODEL,
        "temperature": 0.0,
        "num_predict": 1,
        "raw": False,
    },
    "emb": {
        "model": DEFAULT_EMB_MODEL,
        "vector_size": 1024,
    },
    "rrk": {
        "model": DEFAULT_RRK_MODEL,
        "temperature": 0.0,
        "num_predict": 3,
        "raw": True,
    },
    "query": {
        "using": "Default",
        "ranking": "rrf",
        "limit": 5,
        "offset": 0,
        "with_payload": True,
        "with_vectors": False,
        "prefetch_limit": 0,
        "score_threshold": None,
        "filter": None,
    },
}
