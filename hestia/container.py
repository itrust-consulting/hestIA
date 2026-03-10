
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Set, Callable, Any, Literal

from hestia.settings import Settings
from hestia.providers import OllamaProvider, QdrantDB
from hestia.services import Generator, Embedder, Retriever, RAGenerator


ProviderType = Literal["llm", "db"]
ServiceName = Literal["generate", "chat", "embed", "rerank", "search"]


def _build_ollama(settings: Settings):
    return OllamaProvider(http=settings.LLM_URL)

def _build_qdrant(settings: Settings):
    return QdrantDB(http=settings.DB_URL)

def _build_embedder(providers, settings: Settings, services = None):
    return Embedder(provider=providers["llm"], model=settings.DEFAULT_EMB_MODEL)

def _build_generator(providers, settings: Settings, services = None):
    return Generator(provider=providers["llm"], model=settings.DEFAULT_GEN_MODEL)

def _build_retriever(providers, settings: Settings, services = None):
    return Retriever(provider=providers["db"])

def _build_rag(providers, settings: Settings, services):
    embedder  = services.get("embed")    or _build_embedder(providers, settings, services)
    generator = services.get("generate") or _build_generator(providers, settings, services)
    retriever = services.get("search")   or _build_retriever(providers, settings, services)
    return RAGenerator(embedder=embedder, retriever=retriever, generator=generator)


@dataclass(frozen=True)
class ProviderSpec:
    factory: Callable[[Any], Any]
    type: ProviderType


@dataclass(frozen=True)
class ServiceSpec:
    factory: Callable[[Dict[str, Any], Any, Dict[str, Any]], Any]   # (providers, settings) -> service instance
    deps: Set[str]                                  # required providers: {"llm"}, {"db"}
    singleton_key: Optional[str | List[str]] = None             # services with same key share instance


SERVICE_REGISTRY: Dict[str, ServiceSpec] = {
    "generate": ServiceSpec(factory=_build_generator, deps={"llm"}, singleton_key="llm:generator"),
    "chat":     ServiceSpec(factory=_build_generator, deps={"llm"}, singleton_key="llm:generator"),
    "embed":    ServiceSpec(factory=_build_embedder,  deps={"llm"}, singleton_key="llm:embed"),
    "search":   ServiceSpec(factory=_build_retriever, deps={"db"},  singleton_key="db:search"),
    "rag":      ServiceSpec(factory=_build_rag,       deps={"llm","db"})
}

PROVIDER_REGISTRY: Dict[str, ProviderSpec] = {
    "ollama": ProviderSpec(factory=_build_ollama, type="llm"),
    "qdrant": ProviderSpec(factory=_build_qdrant, type="db"),
}


@dataclass(frozen=True)
class AppStartupConfig:
    llm_backend: Optional[str] = None
    db_backend: Optional[str] = None
    services_to_start: List[ServiceName] = field(default_factory=lambda: ["embed", 
                                                                          "generate", 
                                                                          "chat", 
                                                                          "search"])


@dataclass
class Container:
    settings: Settings
    providers: Dict[str, Any] = field(default_factory=dict)  # keys: "llm", "db", ...
    services: Dict[str, Any] = field(default_factory=dict)   # keys: "embed", 


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

    singleton_cache: Dict[str, Any] = {}

    for svc in cfg.services_to_start:
        spec = SERVICE_REGISTRY.get(svc)
        if spec is None:
            raise ValueError(f"Unknown service '{svc}'.")
        
        missing = [d for d in spec.deps if d not in c.providers]
        if missing:
            raise RuntimeError(f"Cannot start service '{svc}': missing providers {missing}")

        key = spec.singleton_key or svc 
        if key in singleton_cache:
            c.services[svc] = singleton_cache[key]
            continue

        instance = spec.factory(c.providers, settings, c.services)
        singleton_cache[key] = instance
        c.services[svc] = instance

    return c