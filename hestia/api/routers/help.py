import os
import re
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse, PlainTextResponse
from pydantic import BaseModel

from hestia.api.security import get_current_user, assert_admin
from hestia.domain.auth.models import User

router = APIRouter()

_HELP_DIR = Path(
    os.getenv("HESTIA_MANUAL_DIR")
    or Path(__file__).parent.parent.parent.parent / "app" / "data" / "manual"
)
_SLUG_RE   = re.compile(r'^[a-z0-9][a-z0-9-]*$')
_IMG_DIR   = _HELP_DIR / "images"
_SAFE_EXT  = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
_MAX_BYTES = 10 * 1024 * 1024  # 10 MB
_FM_RE     = re.compile(r'^---\r?\n(.*?)\r?\n---\r?\n', re.DOTALL)


class _HelpBody(BaseModel):
    content: str


class _RenameBody(BaseModel):
    filename: str


# ── Helpers ───────────────────────────────────────────────────────────────────

def _validate_slug(section: str) -> str:
    if not _SLUG_RE.match(section):
        raise HTTPException(
            status_code=400,
            detail="Invalid section name — use lowercase letters, digits, and hyphens only",
        )
    return section


def _section_path(section: str) -> Path:
    _validate_slug(section)
    return _HELP_DIR / f"{section}.md"


def _parse_frontmatter(content: str) -> tuple[dict, str]:
    m = _FM_RE.match(content)
    if not m:
        return {}, content
    meta: dict = {}
    for line in m.group(1).splitlines():
        if ':' in line:
            key, _, val = line.partition(':')
            meta[key.strip()] = val.strip().strip('"\'')
    return meta, content[m.end():]


def _extract_title(content: str, slug: str) -> str:
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    return slug.replace("-", " ").title()


def _safe_filename(name: str) -> str:
    if "/" in name or "\\" in name or ".." in name:
        raise HTTPException(status_code=400, detail="Invalid filename")
    return name


# ── Section listing ───────────────────────────────────────────────────────────

@router.get("/help")
def list_help_sections(user: User = Depends(get_current_user)):
    if not _HELP_DIR.exists():
        return {"sections": []}
    items = []
    for p in _HELP_DIR.glob("*.md"):
        slug = p.stem
        if not _SLUG_RE.match(slug):
            continue
        try:
            raw = p.read_text(encoding="utf-8")
        except Exception:
            raw = ""
        meta, body = _parse_frontmatter(raw)
        title = meta.get("title") or _extract_title(body, slug)
        try:
            order = int(meta.get("order", 999))
        except (ValueError, TypeError):
            order = 999
        items.append({"id": slug, "title": title, "_order": order})
    items.sort(key=lambda s: (s["_order"], s["id"]))
    return {"sections": [{"id": s["id"], "title": s["title"]} for s in items]}


# ── Image routes (must come before /help/{section} to avoid shadowing) ────────

@router.get("/help/images")
def list_help_images(user: User = Depends(get_current_user)):
    if not _IMG_DIR.exists():
        return {"images": []}
    images = []
    for p in sorted(_IMG_DIR.iterdir(), key=lambda f: f.stat().st_mtime, reverse=True):
        if p.suffix.lower() in _SAFE_EXT:
            images.append({
                "filename": p.name,
                "url": f"/api/help/images/{p.name}",
                "size": p.stat().st_size,
            })
    return {"images": images}


@router.post("/help/images")
async def upload_help_image(file: UploadFile = File(...), user: User = Depends(get_current_user)):
    assert_admin(user)
    ext = Path(file.filename or "").suffix.lower() or ".png"
    if ext not in _SAFE_EXT:
        raise HTTPException(status_code=400, detail=f"Unsupported format. Allowed: {', '.join(_SAFE_EXT)}")
    data = await file.read(_MAX_BYTES + 1)
    if len(data) > _MAX_BYTES:
        raise HTTPException(status_code=413, detail="Image too large (max 10 MB)")
    _IMG_DIR.mkdir(parents=True, exist_ok=True)
    name = f"{uuid.uuid4().hex}{ext}"
    (_IMG_DIR / name).write_bytes(data)
    return {"url": f"/api/help/images/{name}", "filename": name}


@router.get("/help/images/{filename}")
def get_help_image(filename: str, user: User = Depends(get_current_user)):
    _safe_filename(filename)
    p = _IMG_DIR / filename
    if not p.exists():
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(p)


@router.patch("/help/images/{filename}")
def rename_help_image(filename: str, body: _RenameBody, user: User = Depends(get_current_user)):
    assert_admin(user)
    _safe_filename(filename)
    _safe_filename(body.filename)
    src = _IMG_DIR / filename
    if not src.exists():
        raise HTTPException(status_code=404, detail="Image not found")
    if Path(body.filename).suffix.lower() not in _SAFE_EXT:
        raise HTTPException(status_code=400, detail="Invalid extension")
    dst = _IMG_DIR / body.filename
    if dst.exists():
        raise HTTPException(status_code=409, detail="A file with that name already exists")
    src.rename(dst)
    # Rewrite references in all markdown files
    old_url = f"/api/help/images/{filename}"
    new_url = f"/api/help/images/{body.filename}"
    if _HELP_DIR.exists():
        for md in _HELP_DIR.glob("*.md"):
            try:
                text = md.read_text(encoding="utf-8")
                if old_url in text:
                    md.write_text(text.replace(old_url, new_url), encoding="utf-8")
            except Exception:
                pass
    return {"ok": True, "url": new_url}


@router.delete("/help/images/{filename}")
def delete_help_image(filename: str, user: User = Depends(get_current_user)):
    assert_admin(user)
    _safe_filename(filename)
    p = _IMG_DIR / filename
    if not p.exists():
        raise HTTPException(status_code=404, detail="Image not found")
    p.unlink()
    return {"ok": True}


# ── Section CRUD (dynamic {section} — must come after all static routes) ──────

@router.get("/help/{section}", response_class=PlainTextResponse)
def get_help_section(section: str, user: User = Depends(get_current_user)):
    p = _section_path(section)
    if not p.exists():
        raise HTTPException(status_code=404, detail="Section not found")
    return p.read_text(encoding="utf-8")


@router.put("/help/{section}")
def put_help_section(section: str, body: _HelpBody, user: User = Depends(get_current_user)):
    assert_admin(user)
    p = _section_path(section)
    _HELP_DIR.mkdir(parents=True, exist_ok=True)
    p.write_text(body.content, encoding="utf-8")
    return {"ok": True}


@router.delete("/help/{section}")
def delete_help_section(section: str, user: User = Depends(get_current_user)):
    assert_admin(user)
    p = _section_path(section)
    if not p.exists():
        raise HTTPException(status_code=404, detail="Section not found")
    p.unlink()
    return {"ok": True}
