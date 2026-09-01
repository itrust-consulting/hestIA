from __future__ import annotations

import pathlib
import shutil


def _mirror(source: pathlib.Path, dest: pathlib.Path, *, overwrite: bool) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    for src_file in source.glob("*.yaml"):
        dest_file = dest / src_file.name
        if overwrite or not dest_file.exists():
            shutil.copyfile(src_file, dest_file)


def sync_templates(source_dir: pathlib.Path, dest_dir: pathlib.Path) -> None:
    """base/ is always refreshed from source -- it's coupled to the running
    Runner handler code (hestia/handler.py), never admin-editable. workflows/
    is seeded once, then left alone, so admin edits made through the admin
    UI (hestia/api/routers/workflow_settings.py) live on the persistent
    app_data volume and survive a restart/redeploy, unlike the source tree
    itself (see docker-compose.yml -- only ./app/data is a mounted volume)."""
    _mirror(source_dir / "base", dest_dir / "base", overwrite=True)
    _mirror(source_dir / "workflows", dest_dir / "workflows", overwrite=False)
