import os
import pathlib


VERSION = "alpha_v0.2.1"
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

SERVICES_TO_START = ["encDense", "encSparse","generate", "chat", "search",]

REQUEST_TIMEOUT = (10.0, 800.0)    
# --- DB Settings ---
DEFAULT_DB_URL = "http://192.168.0.34:6333"  
DB_URL = os.getenv("QDRANT_BASE_URL", DEFAULT_DB_URL)

# --- LLM Settings ---
DEFAULT_LLM_URL = "http://192.168.0.34:11434" 
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
UDB_PATH        = APP_DATA.joinpath("./users.db")
CORPUS_DIR      = APP_DATA.joinpath("./corpus_dir/")

# Enable authentication
ENABLE_AUTH = os.getenv("HESTIA_DATA_DIR") or False

# LDAP Settings
ENABLE_LDAP = os.getenv("HESTIA_DATA_DIR") or False
LDAP_SERVER_HOST = "ldaps://ldap.itrust.lu" #os.getenv("HESTIA_DATA_DIR") or "ldaps://ldap.example.com"
LDAP_SERVER_PORT = 636 #os.getenv("HESTIA_DATA_DIR") or 636
LDAP_USE_TLS = os.getenv("HESTIA_DATA_DIR") or True
LDAP_VALIDATE_CERT = True #os.getenv("HESTIA_DATA_DIR") or True
LDAP_APP_DN = "CN=semaphore-binder,OU=services,OU=Users,OU=Niederanven,DC=domitr,DC=itrust,DC=lu" #os.getenv("HESTIA_DATA_DIR") or ""
LDAP_APP_PASSWORD = "F1H19cHrwIBzOX5yFUhuGgm4Aql0deou"# os.getenv("HESTIA_DATA_DIR") or ""
LDAP_SEARCH_BASE = "DC=domitr,DC=itrust,DC=lu" #os.getenv("HESTIA_DATA_DIR") or ""
LDAP_ATTRIBUTE_FOR_USERNAME = "sAMAccountName"#os.getenv("HESTIA_DATA_DIR") or "uid"
LDAP_ATTRIBUTE_FOR_MAIL = "mail" #os.getenv("HESTIA_DATA_DIR") or "mail"
LDAP_MODE = "auto"#os.getenv("HESTIA_DATA_DIR") or "auto"