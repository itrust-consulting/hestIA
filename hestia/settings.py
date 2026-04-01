import os
import pathlib


VERSION = "alpha_v0.2"
PORT = os.getenv("PORT", 5555)

SECRET_KEY = os.getenv("API_KEY")

PROJECT_ROOT_PATH = pathlib.Path(os.path.abspath(os.path.join(__file__, ".."))).parent.absolute()

verbosity = 0  # global verbosity setting for controlling string formatting
PRINT_VERBOSITY = 0  # minimum verbosity to using `print`
STR_VERBOSITY = 3  # minimum verbosity to use verbose `__str__`
MAX_VERBOSITY = 4

LOG_LEVEL = MAX_VERBOSITY

PBKDF2_ITERATIONS = 210_000  # OWASP-recommended range; reasonable default
MAX_HISTORY_PAIRS = 10       # Limit messages loaded into UI


CLASSIFICATION = ["public", "public (pu)", 
                "internal", "internal (in)",
                "confidential", "confidential (co)",
                "restricted", "restricted (re)",
                "secret", "secret (se)"]

LLM_BACKEND     = "ollama"
DB_BACKEND      = "qdrant"

SERVICES_TO_START = ["encDense", "encSparse","generate", "chat","search",]

REQUEST_TIMEOUT = (10.0, 800.0)    
# --- DB Settings ---
DEFAULT_DB_URL = "http://192.168.0.34:6333"  # change to http://qdrant:6333 in docker deployment
DB_URL = os.getenv("QDRANT_BASE_URL", DEFAULT_DB_URL)

# --- LLM Settings ---
DEFAULT_LLM_URL = "http://192.168.0.34:11434" # change to http://ollama:11434 in docker deployment
LLM_URL = os.getenv("OLLAMA_BASE_URL", DEFAULT_LLM_URL)

DEFAULT_GEN_MODEL = "ministral-3:14b"
DEFAULT_EMB_MODEL = "qwen3-embedding:0.6b"
DEFAULT_RRK_MODEL = "dengcao/Qwen3-Reranker-4B:Q8_0"
DEFAULT_CONTEXT_SIZE = 32768
DEFAULT_KEEP_ALIVE = -1

WHITELIST_MODELS = ["ministral-3:14b", "deepseek-r1:32b"]
APP_DATA        = PROJECT_ROOT_PATH.joinpath(os.getenv("HESTIA_DATA_DIR") or "./app/data/")
CSS_FILE        = PROJECT_ROOT_PATH.joinpath("./hestia/frontend/gui/gradio/static/styles.css")
LOG_FILE        = APP_DATA.joinpath("./log.log")
REQ_FILE        = APP_DATA.joinpath("./requests.json")
CDB_PATH        = APP_DATA.joinpath("./uhist.db")
CORPUS_DIR      = APP_DATA.joinpath("./corpus_dir/")


