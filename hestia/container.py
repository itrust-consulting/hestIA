
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Set, Callable, Any, Literal, Protocol, AsyncIterator

from hestia.providers import OllamaProvider, QdrantDB, vLLMProvider
from hestia.services import Generator, DenseEncoder, SparseEncoder, \
    Retriever, LDAPService, UserService, AuthenticationService
from hestia.utils.user_db import UserRepository, create_sqlite_connection
from hestia.config.ldap import load_ldap_config
from hestia.config.auth import load_auth_config

ProviderType = Literal["llm", "db"]
ServiceName = Literal["generate", "chat", "encDense", "encSparse", "search"]

class Settings(Protocol):
    LLM_URL: str
    DB_URL: str
    DEFAULT_GEN_MODEL: str
    DEFAULT_EMB_MODEL: str
    SERVICES_TO_START: List[str]

class AgentProtocol(Protocol):
    name: str
    async def act(self, inv) -> AsyncIterator[str]: ...

def _build_ollama(settings):
    return OllamaProvider(http=settings.LLM_URL)

def _build_vllm(settings):
    return vLLMProvider(chat=settings.LLM_URL, embed=settings.EMB_URL, rerank=settings.RRK_URL)

def _build_qdrant(settings):
    return QdrantDB(http=settings.DB_URL)

def _build_dense_encoder(providers, settings, services = None):
    return DenseEncoder(provider=providers["llm"], model=settings.DEFAULT_EMB_MODEL)

def _build_sparse_encoder(providers, settings, services = None):
    return SparseEncoder()

def _build_generator(providers, settings, services = None):
    return Generator(provider=providers["llm"], model=settings.DEFAULT_GEN_MODEL)

def _build_retriever(providers, settings, services = None):
    return Retriever(provider=providers["db"])


@dataclass(frozen=True)
class ProviderSpec:
    factory: Callable[[Any], Any]
    type: ProviderType


@dataclass(frozen=True)
class ServiceSpec:
    factory: Callable[[Dict[str, Any], Any, Dict[str, Any]], Any]   # (providers, settings) -> service instance
    deps: Set[str]                                  # required providers: {"llm"}, {"db"}
    singleton_key: Optional[str | List[str]] = None             # services with same key share instance


@dataclass(frozen=True)
class AgentSpec:
    factory: Callable[[Dict[str, Any], Dict[str, Any], Settings], AgentProtocol]
    # factory(services, providers, settings) -> agent instance
    deps_services: Set[str] = field(default_factory=set)  # e.g., {"generate","embed","search"}
    deps_providers: Set[str] = field(default_factory=set)  # rare, but available
    singleton_key: Optional[str] = None                   # share agent singleton if needed


PROVIDER_REGISTRY: Dict[str, ProviderSpec] = {
    "ollama":   ProviderSpec(factory=_build_ollama, type="llm"),
    "vllm":     ProviderSpec(factory=_build_vllm, type="llm"),
    "qdrant":   ProviderSpec(factory=_build_qdrant, type="db"),
}

SERVICE_REGISTRY: Dict[str, ServiceSpec] = {
    "generate":     ServiceSpec(factory=_build_generator, deps={"llm"}, singleton_key="llm:generator"),
    "chat":         ServiceSpec(factory=_build_generator, deps={"llm"}, singleton_key="llm:generator"),
    "encDense":     ServiceSpec(factory=_build_dense_encoder,  deps={"llm"}, singleton_key="llm:embed"),
    "encSparse":    ServiceSpec(factory=_build_sparse_encoder,  deps={}, singleton_key="encSparse"),
    "search":       ServiceSpec(factory=_build_retriever, deps={"db"},  singleton_key="db:search"),
}

AGENT_REGISTRY: Dict[str, AgentSpec] = {
    "audit":    AgentSpec(factory=None),
    "asset":    AgentSpec(factory=None)
}


@dataclass(frozen=True)
class AppStartupConfig:
    llm_backend:    str
    db_backend:     str
    services_to_start: List[ServiceName] = field(default_factory=lambda: ["encDense", 
                                                                          "encSparse"
                                                                          "generate", 
                                                                          "chat", 
                                                                          "search"])
    agents_to_start: List[str] = field(default_factory=list)
    enable_auth: bool = False
    enable_ldap: bool = False


@dataclass
class Container:
    settings: Settings
    providers: Dict[str, Any] = field(default_factory=dict)  # keys: "llm", "db", ...
    services: Dict[str, Any] = field(default_factory=dict)   # keys: "embed", 
    agents: Dict[str, Any] = field(default_factory=dict)

def _build_provider(type: str, backend_key: str, settings) -> Any:
    spec = PROVIDER_REGISTRY.get(backend_key)
    if not spec:
        raise ValueError(f"Unknown backend '{backend_key}'")
    if spec.type != type:
        raise ValueError(f"Backend '{backend_key}' is type='{spec.type}', not type='{type}'")
    return spec.factory(settings)

def build_container(settings, cfg: AppStartupConfig) -> Container:
    c = Container(settings)
    
    if cfg.llm_backend:
        c.providers["llm"] = _build_provider("llm", cfg.llm_backend, settings)

    if cfg.db_backend:
        c.providers["db"] = _build_provider("db", cfg.db_backend, settings)

    if cfg.enable_auth:
        get_conn, close, lock = create_sqlite_connection(settings.UDB_PATH)
        repo = UserRepository(get_conn, lock)
        usvc = UserService(repo)
        repo.initialize()

        auth_config = load_auth_config()

        ldap = None
        if auth_config.enable_ldap:
            ldap_config = load_ldap_config()

            ldap = LDAPService(
                host=ldap_config.host,
                port=ldap_config.port,
                search_base=ldap_config.search_base,
                bind_dn=ldap_config.bind_dn,
                bind_password=ldap_config.bind_password,
                user_attribute=ldap_config.user_attribute,
                mail_attribute=ldap_config.mail_attribute,
                use_ssl=ldap_config.use_ssl,
                validate_cert=ldap_config.validate_cert,
                allowed_groups=ldap_config.allowed_groups,
                mode=ldap_config.mode
            )

        c.services["auth"] = AuthenticationService(usvc, ldap, config=auth_config)
        c.services["users"] = usvc
        close()

    singleton_cache: Dict[str, Any] = {}

    for svc in cfg.services_to_start:
        spec = SERVICE_REGISTRY.get(svc)
        if spec is None:
            raise ValueError(f"Unknown service '{svc}'.")
        
        missing_dep = [d for d in spec.deps if d not in c.providers]
        if missing_dep:
            raise RuntimeError(f"Cannot start service '{svc}': missing providers {missing_dep}")

        key = spec.singleton_key or svc 
        if key in singleton_cache:
            c.services[svc] = singleton_cache[key]
            continue

        instance = spec.factory(c.providers, settings, c.services)
        singleton_cache[key] = instance
        c.services[svc] = instance

    for agent in cfg.agents_to_start:
        spec = AGENT_REGISTRY.get(agent)
        if spec is None:
            raise ValueError(f"Unkown agent '{agent}'.")

        missing_dep = [d for d in spec.deps_services if d not in c.services]
        if missing_dep:
            raise RuntimeError(f"Cannot start service '{svc}': missing providers {missing_dep}")
        
        key = spec.singleton_key or agent
        if key in singleton_cache:
            c.agents[svc] = singleton_cache[key]
            continue

        instance = spec.factory(c.providers, settings, c.services)
        singleton_cache[key] = instance
        c.agents[svc] = instance

    return c