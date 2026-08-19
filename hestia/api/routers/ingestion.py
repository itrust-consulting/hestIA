from __future__ import annotations

import asyncio
import json
import tempfile
import time
from pathlib import Path

from fastapi import APIRouter, Depends, Form, UploadFile, File
from pydantic import BaseModel

from hestia.api.dependencies import get_handler
from hestia.api.security import get_current_user, assert_collection_moderator
from hestia.application.ingestion import IngestionPipeline, IngestionRequest
from hestia.domain.auth.models import User
from hestia.domain.rag.classification import Classification
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
    if ext == ".json":
        from hestia.infrastructure.parsers.json import JSONParser
        return JSONParser(file=str(file_path))
    if ext == ".csv":
        from hestia.infrastructure.parsers.csv import CSVParser
        return CSVParser(file=str(file_path))
    if ext == ".txt":
        from hestia.infrastructure.parsers.txt import TXTParser
        return TXTParser(file=str(file_path))
    if ext in (".md", ".markdown"):
        from hestia.infrastructure.parsers.md import MarkdownParser
        return MarkdownParser(file=str(file_path))
    if ext == ".pptx":
        from hestia.infrastructure.parsers.pptx import PPTXParser
        return PPTXParser(file=str(file_path))
    from hestia.domain.exceptions import ConfigurationError
    raise ConfigurationError(f"No parser registered for '{ext}'")


# @MRS-014, @MRS-099
@router.post("/parse")
async def parse_document(
    file: UploadFile = File(...),
    itrust_template: bool = Form(False),
    _user: User = Depends(get_current_user),
):
    """Parse a document and return its metadata without ingesting."""
    import logging
    _log = logging.getLogger("hestia.system")
    _log.info("start parsing ..", extra={"file": file.filename})

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


# @MRS-010, @MRS-060, @MRS-102
@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    collection: str = Form(...),
    tenants: str = Form("[]"),
    itrust_template: bool = Form(False),
    metadata_overrides: str = Form("{}"),
    language: str = Form("english"),
    selected_sheets: str = Form("[]"),
    chunking_strategy: str = Form("auto"),
    max_chars: int | None = Form(None),
    max_depth: int | None = Form(None),
    sync_id: str | None = Form(None),
    content_hash: str | None = Form(None),
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
        chunking_strategy=chunking_strategy,
        max_chars=max_chars,
        max_depth=max_depth,
    )
    result = None
    deduped = False
    duplicate_of: str | None = None

    if sync_id and content_hash:
        sync_repo = h.container.services["sync_manifest"]
        owner = sync_repo.claim_owner(collection, content_hash, file.filename)
        if owner == file.filename:
            result = await asyncio.to_thread(pipeline.ingest, req)
        else:
            # Identical content already owned by a different source_uri in this
            # collection — skip parsing/embedding entirely and just make sure
            # the owner's classification is at least as strict as requested.
            deduped = True
            duplicate_of = owner
            classification_override = overrides.get("classification")
            if isinstance(classification_override, str):
                requested = Classification.from_label(classification_override)
                if requested is not None:
                    h.container.providers["db"].bump_classification(collection, owner, requested.level)
        sync_repo.upsert_entry(collection, sync_id, file.filename, content_hash, int(time.time()))
    else:
        result = await asyncio.to_thread(pipeline.ingest, req)

    Path(tmp_path).unlink(missing_ok=True)

    return {
        "ok": True,
        "collection": collection,
        "source": result.source if result else duplicate_of,
        "n_chunks": result.n_chunks if result else 0,
        "n_upserted": result.n_upserted if result else 0,
        "elapsed_ms": result.elapsed_ms if result else 0.0,
        "deduped": deduped,
        "duplicate_of": duplicate_of,
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


@router.get("/collections/document-counts")
def get_document_counts(
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(get_current_user),
):
    counts = h.container.providers["db"].document_counts()

    perms = user.permissions
    if perms.is_admin:
        return {"counts": counts}

    allowed = perms.allowed_collections
    if "*" in allowed and allowed["*"].access:
        return {"counts": counts}

    permitted = {name for name, perm in allowed.items() if perm.access}
    return {"counts": {name: c for name, c in counts.items() if name in permitted}}


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


@router.get("/collections/{name}/documents")
def get_document(
    name: str,
    source_uri: str,
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(get_current_user),
):
    assert_collection_moderator(user, name, h)
    doc = h.container.providers["db"].get_document(name, source_uri)
    if doc is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Document '{source_uri}' not found in '{name}'.")
    return doc


@router.delete("/collections/{name}/documents")
def delete_document(
    name: str,
    source_uri: str,
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(get_current_user),
):
    assert_collection_moderator(user, name, h)

    db = h.container.providers["db"]
    sync_repo = h.container.services["sync_manifest"]

    should_delete_content = True
    content_hash = sync_repo.get_hash_for_source(name, source_uri)
    if content_hash is not None:
        owner = sync_repo.get_owner(name, content_hash)
        if owner is not None and owner != source_uri:
            # This source_uri never had real Qdrant content of its own — it was
            # a deduped reference piggybacking on another source's upload.
            should_delete_content = False
        elif owner is not None and owner == source_uri:
            remaining = [u for u in sync_repo.get_references(name, content_hash) if u != source_uri]
            if remaining:
                new_owner = remaining[0]
                sync_repo.reassign_owner(name, content_hash, new_owner)
                db.rename_source(name, source_uri, new_owner)
                should_delete_content = False
            else:
                sync_repo.remove_owner(name, content_hash)

    if should_delete_content:
        db.delete_document(name, source_uri)
        sparse_enc = h.container.services.get("encSparse")
        if sparse_enc is not None:
            sparse_enc.remove_document(source_uri, name)

    sync_repo.delete_entry(name, source_uri)
    return {"ok": True, "deleted": source_uri}


class UpdateDocumentMetadataRequest(BaseModel):
    source_uri: str
    metadata: dict


@router.patch("/collections/{name}/documents")
def update_document_metadata(
    name: str,
    body: UpdateDocumentMetadataRequest,
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(get_current_user),
):
    assert_collection_moderator(user, name, h)

    matched_levels = [
        c.level
        for v in body.metadata.values()
        if isinstance(v, str) and (c := Classification.from_label(v)) is not None
    ]
    level = max(matched_levels) if matched_levels else None

    ok = h.container.providers["db"].update_document_metadata(name, body.source_uri, body.metadata, level)
    if not ok:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Document '{body.source_uri}' not found in '{name}'.")
    return {"ok": True}


class SyncManifestEntry(BaseModel):
    path: str        # relative path, matches what will be sent as source_uri on upload
    checksum: str    # client-computed SHA-256 hex digest


class SyncDiffRequest(BaseModel):
    sync_id: str
    manifest: list[SyncManifestEntry]


@router.post("/collections/{name}/sync/diff")
def sync_diff(
    name: str,
    body: SyncDiffRequest,
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(get_current_user),
):
    """Diff a client-supplied file manifest against previously-synced documents
    tagged with the same sync_id, without touching any documents outside that
    scope (manual uploads or other sync sources sharing the collection)."""
    assert_collection_moderator(user, name, h)
    sync_repo = h.container.services["sync_manifest"]
    last_synced_at = sync_repo.get_last_synced_at(name, body.sync_id)
    existing = sync_repo.get_manifest(name, body.sync_id)
    incoming = {m.path: m.checksum for m in body.manifest}

    added = sorted(set(incoming) - set(existing))
    deleted = sorted(set(existing) - set(incoming))
    modified = sorted(p for p in (set(incoming) & set(existing)) if incoming[p] != existing[p])
    unmodified_count = len(incoming) - len(added) - len(modified)

    # Let the client pre-fill a modified document's classification with
    # whatever's already stored, rather than defaulting to "auto-detect" for
    # a file whose content changed slightly but is still the same document.
    levels = h.container.providers["db"].get_classifications(name, modified)
    previous_classifications = {
        uri: cls.aliases[0]
        for uri, level in levels.items()
        if (cls := Classification.from_level(level)) is not None
    }

    return {
        "added": added, "modified": modified, "deleted": deleted, "unmodified_count": unmodified_count,
        "last_synced_at": last_synced_at, "previous_classifications": previous_classifications,
    }


class SyncCompleteRequest(BaseModel):
    sync_id: str


@router.post("/collections/{name}/sync/complete")
def sync_complete(
    name: str,
    body: SyncCompleteRequest,
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(get_current_user),
):
    """Record that a sync run for this source finished — deliberately separate
    from sync_diff, so a run that's only diffed and then cancelled doesn't
    count as a completed sync."""
    assert_collection_moderator(user, name, h)
    h.container.services["sync_manifest"].mark_synced(name, body.sync_id, int(time.time()))
    return {"ok": True}


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
    h.container.services["sync_manifest"].delete_collection(name)
    return {"ok": True, "deleted": name}
