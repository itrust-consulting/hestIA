from fastapi import APIRouter, Depends, HTTPException

from hestia.api.dependencies import get_handler
from hestia.api.security import assert_admin, get_current_user
from hestia.api.schemas.requests import LLMConnectionCreateRequest, LLMConnectionTestRequest, LLMConnectionUpdateRequest
from hestia.container import build_db_provider, build_llm_provider
from hestia.domain.auth.models import User
from hestia.domain.exceptions import ProviderError
from hestia.handler import RequestHandler
from hestia.infrastructure.logging.audit import audit, audited

router = APIRouter()


@router.get("/llm/connections")
def list_connections(
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(get_current_user),
):
    assert_admin(user)
    return {"connections": h.container.services["llm_settings"].list_connections()}


@router.post("/llm/connections")
def create_connection(
    req: LLMConnectionCreateRequest,
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(get_current_user),
):
    assert_admin(user)
    if not req.base_url.strip():
        raise HTTPException(400, "Base URL is required")
    detail = {"purpose": req.purpose, "backend_type": req.backend_type}
    try:
        connection_id = h.container.services["llm_settings"].create_connection(
            purpose=req.purpose, backend_type=req.backend_type, base_url=req.base_url.strip(), api_key=req.api_key,
        )
    except Exception as e:
        audit.connection_action(actor_id=str(user.id), action="connection_create", target=req.purpose,
                                 detail=detail, success=False, reason=str(e))
        raise
    audit.connection_action(actor_id=str(user.id), action="connection_create", target=str(connection_id),
                             detail=detail, success=True)
    return {"ok": True, "id": connection_id}


@router.post("/llm/connections/test")
def test_connection(
    req: LLMConnectionTestRequest,
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(get_current_user),
):
    """Tests connectivity for a backend_type/base_url/api_key combo that
    isn't (yet) saved -- gates both creating a new connection and saving
    edits to an existing one's URL/API key, before either commits."""
    assert_admin(user)
    if not req.base_url.strip():
        raise HTTPException(400, "Base URL is required")

    api_key = req.api_key
    if not api_key and req.connection_id is not None:
        existing = h.container.services["llm_settings"].get_connection(req.connection_id)
        if existing is not None:
            api_key = existing["api_key"]

    try:
        if req.backend_type == "qdrant":
            build_db_provider("qdrant", req.base_url.strip(), api_key).collections
        else:
            build_llm_provider(req.backend_type, req.base_url.strip(), api_key, h.container.settings.request_timeout).models
        return {"ok": True}
    except ProviderError as e:
        return {"ok": False, "error": str(e)}
    except Exception as e:
        return {"ok": False, "error": f"Unexpected error: {e}"}


@router.put("/llm/connections/{connection_id}")
def update_connection(
    connection_id: int,
    req: LLMConnectionUpdateRequest,
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(get_current_user),
):
    assert_admin(user)
    if not req.base_url.strip():
        raise HTTPException(400, "Base URL is required")
    # Duplicated (not shared -- no cross-language codegen here) in the
    # frontend at hestia-ui/.../admin/settings/connections/+page.svelte's
    # save handler. Keep both in sync -- the frontend copy only pre-empts a
    # round-trip for an invalid pair; this is the actual enforcement.
    if (
        req.compaction_enabled
        and req.compaction_context_window is not None
        and req.compaction_summary_length is not None
        and req.compaction_summary_length >= req.compaction_context_window
    ):
        raise HTTPException(400, "Compaction summary length must be less than the context window.")
    repo = h.container.services["llm_settings"]
    if repo.get_connection(connection_id) is None:
        raise HTTPException(404, "Connection not found")
    with audited(audit.connection_action, actor_id=str(user.id), action="connection_update", target=str(connection_id)):
        repo.update_connection(
            connection_id=connection_id, base_url=req.base_url.strip(), api_key=req.api_key,
            model=req.model.strip(), params=req.params,
            compaction_enabled=req.compaction_enabled, compaction_model=req.compaction_model,
            compaction_context_window=req.compaction_context_window,
            compaction_summary_length=req.compaction_summary_length,
        )
    h.container.apply_connection_update(connection_id)
    return {"ok": True}


@router.delete("/llm/connections/{connection_id}")
def delete_connection(
    connection_id: int,
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(get_current_user),
):
    assert_admin(user)
    repo = h.container.services["llm_settings"]
    row = repo.get_connection(connection_id)
    purpose = row["purpose"] if row else None
    with audited(audit.connection_action, actor_id=str(user.id), action="connection_delete", target=str(connection_id),
                 detail={"purpose": purpose}):
        repo.delete_connection(connection_id=connection_id)
    h.container.apply_connection_delete(connection_id, purpose)
    return {"ok": True}


@router.post("/llm/connections/{connection_id}/activate")
def activate_connection(
    connection_id: int,
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(get_current_user),
):
    """Makes this connection the active one for its purpose (deactivating
    any siblings), and rewires the purpose's live service to it -- reuses
    apply_connection_update, which already does exactly what's needed here:
    look up the row, rebuild the Qdrant client in place for vector_db, or
    get_or_build_provider + rewire the Generator/DenseEncoder otherwise."""
    assert_admin(user)
    repo = h.container.services["llm_settings"]
    if repo.get_connection(connection_id) is None:
        raise HTTPException(404, "Connection not found")
    with audited(audit.connection_action, actor_id=str(user.id), action="connection_activate", target=str(connection_id)):
        repo.activate_connection(connection_id=connection_id)
    h.container.apply_connection_update(connection_id)
    return {"ok": True}


@router.get("/llm/connections/{connection_id}/models")
def list_connection_models(
    connection_id: int,
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(get_current_user),
):
    """Fetches the live model list from the connection (also serves as a
    connectivity test) -- populates the model dropdown in the settings modal."""
    assert_admin(user)
    repo = h.container.services["llm_settings"]
    row = repo.get_connection(connection_id)
    if row is None:
        raise HTTPException(404, "Connection not found")
    if row["purpose"] == "vector_db":
        return {"ok": False, "error": "Model listing isn't applicable to a vector database connection.", "models": []}
    try:
        provider = h.container.get_or_build_provider(connection_id)
        models = provider.models.get("models", [])
        return {"ok": True, "models": [m.get("model") for m in models if m.get("model")]}
    except ProviderError as e:
        return {"ok": False, "error": str(e), "models": []}
    except Exception as e:
        return {"ok": False, "error": f"Unexpected error: {e}", "models": []}
