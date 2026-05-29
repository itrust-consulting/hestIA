from __future__ import annotations

import asyncio
import json
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, Form, UploadFile, File

from hestia.api.dependencies import get_handler
from hestia.api.security import get_current_user, assert_collection_moderator
from hestia.application.ingestion import IngestionPipeline, IngestionRequest
from hestia.domain.auth.models import User
from hestia.handler import RequestHandler

router = APIRouter()


def _pipeline(h: RequestHandler) -> IngestionPipeline:
    svc = h.container.services.get("ingestion")
    if svc is None:
        from hestia.domain.exceptions import ConfigurationError
        raise ConfigurationError("Ingestion service not available")
    return svc


def _save_temp(file_bytes: bytes, suffix: str) -> str:
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(file_bytes)
        return tmp.name


def _get_parser_direct(file_path: Path, itrust_template: bool):
    from hestia.application.ingestion import SUPPORTED_EXTENSIONS
    from hestia.domain.exceptions import ValidationError as DomainValidationError

    ext = file_path.suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise DomainValidationError(
            f"File type '{ext}' not supported. Supported: {', '.join(SUPPORTED_EXTENSIONS)}"
        )
    if ext == ".docx":
        if itrust_template:
            from hestia.infrastructure.parsers.docx import ITRDOCXParser
            return ITRDOCXParser(file=str(file_path))
        from hestia.infrastructure.parsers.docx import DOCXParser
        return DOCXParser(file=str(file_path))
    if ext == ".pdf":
        if itrust_template:
            from hestia.infrastructure.parsers.pdf import ITRPDFParser
            return ITRPDFParser(file=str(file_path))
        from hestia.infrastructure.parsers.pdf import PDFParser
        return PDFParser(file=str(file_path))
    if ext in (".xlsx", ".xlsm"):
        if itrust_template:
            from hestia.infrastructure.parsers.xlsx import ITRXLSXParser
            return ITRXLSXParser(file=str(file_path))
        from hestia.infrastructure.parsers.xlsx import XLSXParser
        return XLSXParser(file=str(file_path))


@router.post("/parse")
async def parse_document(
    file: UploadFile = File(...),
    itrust_template: bool = Form(False),
    _user: User = Depends(get_current_user),
):
    """Parse a document and return its metadata without ingesting."""
    import logging
    _log = logging.getLogger("hestia.system")

    data = await file.read()
    suffix = Path(file.filename).suffix.lower()
    tmp_path = _save_temp(data, suffix)
    parser = None
    try:
        parser = _get_parser_direct(Path(tmp_path), itrust_template)
        metadata = parser.get_metadata(builtIn_only=not itrust_template, mask_name="rag_default")
        metadata["source"] = Path(file.filename).stem
        metadata["source_uri"] = file.filename
        markdown = parser.to_markdown()
        return {"metadata": metadata, "markdown": markdown, "filename": file.filename}
    except Exception as exc:
        import traceback
        tb = traceback.format_exc()
        _log.warning("parse_document_failed", extra={"file": file.filename, "error": str(exc), "traceback": tb})
        return {"metadata": {}, "markdown": "", "filename": file.filename, "parse_error": str(exc), "traceback": tb}
    finally:
        if parser is not None:
            parser.close()
        Path(tmp_path).unlink(missing_ok=True)


@router.post("/upload")
async def ingest_document(
    file: UploadFile = File(...),
    collection: str = Form(...),
    tenants: str = Form("[]"),
    itrust_template: bool = Form(False),
    metadata_overrides: str = Form("{}"),
    language: str = Form("english"),
    selected_sheets: str = Form("[]"),
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(get_current_user),
):
    data = await file.read()
    suffix = Path(file.filename).suffix.lower()
    tmp_path = _save_temp(data, suffix)

    try:
        tenants_list: list[str] = json.loads(tenants) if tenants else []
    except json.JSONDecodeError:
        tenants_list = []

    try:
        overrides = json.loads(metadata_overrides) if metadata_overrides else {}
    except json.JSONDecodeError:
        overrides = {}

    try:
        sheets_list: list[str] | None = json.loads(selected_sheets) if selected_sheets else None
        if sheets_list == []:
            sheets_list = None
    except json.JSONDecodeError:
        sheets_list = None

    assert_collection_moderator(user, collection, h)

    pipeline = _pipeline(h)
    req = IngestionRequest(
        file_path=tmp_path,
        collection=collection,
        tenants=tenants_list,
        uploaded_by=user.username,
        classification_labels=h.container.settings.classification_labels,
        itrust_template=itrust_template,
        original_filename=file.filename,
        metadata_overrides=overrides,
        language=language,
        selected_sheets=sheets_list,
    )
    result = await asyncio.to_thread(pipeline.ingest, req)

    Path(tmp_path).unlink(missing_ok=True)

    return {
        "ok": True,
        "collection": result.collection,
        "source": result.source,
        "n_chunks": result.n_chunks,
        "n_upserted": result.n_upserted,
        "elapsed_ms": result.elapsed_ms,
    }


@router.get("/collections")
def list_collections(
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(get_current_user),
):
    all_collections = h.container.providers["db"].collections.get("collections", [])

    perms = user.permissions
    if perms.is_admin:
        return {"collections": all_collections}

    allowed = perms.allowed_collections
    if "*" in allowed and allowed["*"].access:
        return {"collections": all_collections}

    permitted = {name for name, perm in allowed.items() if perm.access}
    return {"collections": [c for c in all_collections if c["name"] in permitted]}


@router.get("/collections/{name}")
def get_collection(
    name: str,
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(get_current_user),
):
    result = h.container.providers["db"].get_collection(name)
    if result is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Collection '{name}' not found.")
    users_svc = h.container.services.get("users")
    if users_svc:
        grants = users_svc.get_collection_grants(name)
        owner = grants.get("owner")
        is_moderator = owner and owner["id"] in user.permissions.moderated_tenants
        if user.permissions.is_admin or is_moderator:
            result["tenants"] = [t["abbreviation"] for t in grants["access"]]
            result["owner_tenant"] = owner
    return result


@router.delete("/collections/{name}/documents")
def delete_document(
    name: str,
    source_uri: str,
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(get_current_user),
):
    assert_collection_moderator(user, name, h)
    h.container.providers["db"].delete_document(name, source_uri)
    sparse_enc = h.container.services.get("encSparse")
    if sparse_enc is not None:
        sparse_enc.remove_document(source_uri, name)
    return {"ok": True, "deleted": source_uri}


@router.delete("/collections/{name}")
def delete_collection(
    name: str,
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(get_current_user),
):
    assert_collection_moderator(user, name, h)
    deleted = h.container.providers["db"].delete_collection(name)
    if not deleted:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Collection '{name}' not found.")
    users_svc = h.container.services.get("users")
    if users_svc:
        users_svc.remove_collection_grants(name)
    sparse_enc = h.container.services.get("encSparse")
    if sparse_enc is not None:
        sparse_enc.delete_corpus(name)
    return {"ok": True, "deleted": name}
