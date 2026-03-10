import os
import pathlib
from typing import Optional, List
from dataclasses import dataclass, field

from hestia.schemas import types

# --- Settings ---
PROJECT_ROOT_PATH = pathlib.Path(os.path.abspath(os.path.join(__file__, ".."))).parent.absolute()

# --- Logging --- 
CSS_FILE = PROJECT_ROOT_PATH.joinpath("./frontend/gui/static/styles.css")
APP_DATA = PROJECT_ROOT_PATH.joinpath("./app/data/")
LOG_FILE = APP_DATA.joinpath("./log.log")
REQ_FILE = APP_DATA.joinpath("./requests.json")

# --- DB Config ---
CDB_PATH = APP_DATA.joinpath("./uhist.db")
PBKDF2_ITERATIONS = 210_000  # OWASP-recommended range; reasonable default
MAX_HISTORY_PAIRS = 10       # Limit messages loaded into UI


verbosity = 0  # global verbosity setting for controlling string formatting
PRINT_VERBOSITY = 0  # minimum verbosity to using `print`
STR_VERBOSITY = 3  # minimum verbosity to use verbose `__str__`
MAX_VERBOSITY = 4

LOG_LEVEL = MAX_VERBOSITY

# --- HTTP ---
REQUEST_TIMEOUT = (10.0, 800.0)


# --- DB Settings ---
DEFAULT_DB_URL = "http://192.168.0.34:6333"  # change to http://qdrant:6333 in docker deployment
DB_URL = os.getenv("QDRANT_BASE_URL", DEFAULT_DB_URL)


# --- LLM Settings ---
DEFAULT_LLM_URL = "http://192.168.0.34:11434" # change to http://ollama:11434 in docker deployment
LLM_URL = os.getenv("OLLAMA_BASE_URL", DEFAULT_LLM_URL)

DEFAULT_CONTEXT_SIZE = 128000
DEFAULT_GEN_MODEL = "ministral-3:14b"
DEFAULT_EMB_MODEL = "qwen3-embedding:0.6b"
DEFAULT_RRK_MODEL = "dengcao/Qwen3-Reranker-4B:Q8_0"
DEFAULT_KEEP_ALIVE = -1
WHITELIST_MODELS = ["ministral-3:14b", "deepseek-r1:32b"]


DENSE_DIM = 1024
DEFAULT_OUTPUT_DIR = "./dump/textsplitter/"

SUPPORTED_EXTENSIONS = [".docx", ".pdf"]
CLASSIFICATION = ["public", "public (pu)", 
                  "internal", "internal (in)",
                  "confidential", "confidential (co)",
                  "restricted", "restricted (re)",
                  "secret", "secret (se)"]


@dataclass
class Settings:
    LLM_BACKEND: Optional[types.LLMBackend] = field(default="ollama")
    DB_BACKEND: Optional[types.DBBackend] = field(default="qdrant")

    SERVICES_TO_START: List[types.ServiceName] = field(default_factory=lambda: ["embed", 
                                                                          "generate", 
                                                                          "chat",
                                                                          "search",
                                                                          "rag"])

    REQUEST_TIMEOUT = (10.0, 800.0)    
    # --- DB Settings ---
    DEFAULT_DB_URL = "http://192.168.0.34:6333"  # change to http://qdrant:6333 in docker deployment
    DB_URL = os.getenv("QDRANT_BASE_URL", DEFAULT_DB_URL)

    # --- LLM Settings ---
    DEFAULT_LLM_URL = "http://192.168.0.34:11434" # change to http://ollama:11434 in docker deployment
    LLM_URL = os.getenv("OLLAMA_BASE_URL", DEFAULT_LLM_URL)

    DEFAULT_CONTEXT_SIZE = 32768
    DEFAULT_GEN_MODEL = "ministral-3:14b"
    DEFAULT_EMB_MODEL = "qwen3-embedding:0.6b"
    DEFAULT_RRK_MODEL = "dengcao/Qwen3-Reranker-4B:Q8_0"

    WHITELIST_MODELS = ["ministral-3:14b", "deepseek-r1:32b"]
    APP_DATA = PROJECT_ROOT_PATH.joinpath("./app/data/")
    CSS_FILE = PROJECT_ROOT_PATH.joinpath("./hestia/frontend/gui/static/styles.css")
    LOG_FILE = APP_DATA.joinpath("./log.log")
    REQ_FILE = APP_DATA.joinpath("./requests.json")

    CORPUS_INDEX = APP_DATA.joinpath("./corpus_index.json")

    API_URL = "http://0.0.0.0:7860"

    DENSE_DIM = 1024

