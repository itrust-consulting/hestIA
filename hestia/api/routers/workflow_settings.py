import re

import yaml
from fastapi import APIRouter, Depends, HTTPException

from hestia.api.dependencies import get_handler
from hestia.api.security import assert_admin, get_current_user
from hestia.api.schemas.requests import WorkflowCreateRequest, WorkflowUpdateRequest
from hestia.domain.auth.models import User
from hestia.domain.exceptions import ValidationError
from hestia.domain.rag.graph import validate_workflow_graph
from hestia.handler import RequestHandler
from hestia.infrastructure.logging.audit import audit

router = APIRouter()

# Admin-supplied names are interpolated directly into a filesystem path
# (_live_path/_source_path) -- this allowlist is what used to be enforced
# implicitly by the old ExecType Literal[...] path-param type, back when
# only the 4 built-in names were ever accepted. Now that any name can be
# created, every handler below validates it explicitly first.
_NAME_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,64}$")

_STARTER_YAML = """entrypoint: Chat1
exitpoints: [Chat1]
nodes:
  - id: Chat1
    type: Chat
    inputs:
      history: ${history}
      last_user_message: ${last_user_message}
    outputs:
      response: response
"""


def _validate_workflow_name(name: str) -> None:
    if not _NAME_PATTERN.match(name):
        raise HTTPException(400, "Workflow name must be 1-64 characters, letters/numbers/underscore/hyphen only.")


def _source_path(h: RequestHandler, name: str):
    return h.container.settings.project_root / "hestia" / "templates" / "workflows" / f"{name}.yaml"


def _live_path(h: RequestHandler, name: str):
    return h.container.settings.app_data / "templates" / "workflows" / f"{name}.yaml"


def _validate_and_write(h: RequestHandler, name: str, yaml_text: str) -> None:
    try:
        root = yaml.safe_load(yaml_text)
    except yaml.YAMLError as e:
        raise HTTPException(400, f"Invalid YAML: {e}")
    if not isinstance(root, dict):
        raise HTTPException(400, "Workflow YAML must be a mapping with 'entrypoint' and 'nodes'.")
    try:
        validate_workflow_graph(root)
    except ValidationError as e:
        raise HTTPException(400, e.message)

    live = _live_path(h, name)
    live.parent.mkdir(parents=True, exist_ok=True)
    live.write_text(yaml_text, encoding="utf-8")
    h.builder.repo.invalidate()


@router.get("/workflows")
def list_workflows(
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(get_current_user),
):
    assert_admin(user)
    live_dir = h.container.settings.app_data / "templates" / "workflows"
    workflows = []
    for live in sorted(live_dir.glob("*.yaml")):
        name = live.stem
        source = _source_path(h, name)
        yaml_text = live.read_text(encoding="utf-8")
        is_builtin = source.exists()
        is_custom = (not is_builtin) or yaml_text != source.read_text(encoding="utf-8")
        workflows.append({"exec_type": name, "yaml_text": yaml_text, "is_custom": is_custom, "is_builtin": is_builtin})
    return {"workflows": workflows}


@router.post("/workflows")
def create_workflow(
    req: WorkflowCreateRequest,
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(get_current_user),
):
    assert_admin(user)
    _validate_workflow_name(req.name)
    if _live_path(h, req.name).exists():
        raise HTTPException(400, f"A workflow named '{req.name}' already exists.")

    yaml_text = req.yaml_text if req.yaml_text is not None else _STARTER_YAML
    _validate_and_write(h, req.name, yaml_text)

    audit.admin_action(actor_id=str(user.id), action="workflow_create", target=req.name)
    return {"ok": True}


@router.put("/workflows/{exec_type}")
def update_workflow(
    exec_type: str,
    req: WorkflowUpdateRequest,
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(get_current_user),
):
    assert_admin(user)
    _validate_workflow_name(exec_type)
    _validate_and_write(h, exec_type, req.yaml_text)

    audit.admin_action(actor_id=str(user.id), action="workflow_update", target=exec_type)
    return {"ok": True}


@router.delete("/workflows/{exec_type}")
def reset_or_delete_workflow(
    exec_type: str,
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(get_current_user),
):
    """Built-in names (one of the 4 shipped in hestia/templates/workflows/)
    reset the live copy back to the shipped default. Admin-created names
    have no default to fall back to, so this actually deletes the file."""
    assert_admin(user)
    _validate_workflow_name(exec_type)
    source = _source_path(h, exec_type)
    live = _live_path(h, exec_type)

    if source.exists():
        live.parent.mkdir(parents=True, exist_ok=True)
        live.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
        h.builder.repo.invalidate()
        audit.admin_action(actor_id=str(user.id), action="workflow_reset", target=exec_type)
    else:
        if not live.exists():
            raise HTTPException(404, f"Workflow '{exec_type}' not found.")
        live.unlink()
        h.builder.repo.invalidate()
        audit.admin_action(actor_id=str(user.id), action="workflow_delete", target=exec_type)
    return {"ok": True}
