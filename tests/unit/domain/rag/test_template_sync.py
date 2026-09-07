from __future__ import annotations

from hestia.domain.rag.template_sync import sync_templates


def _write(path, name, content):
    path.mkdir(parents=True, exist_ok=True)
    (path / name).write_text(content)


class TestSyncTemplates:

    def test_creates_dest_directories_when_missing(self, tmp_path):
        source = tmp_path / "source"
        dest = tmp_path / "dest"
        _write(source / "base", "chat.yaml", "base-v1")
        _write(source / "workflows", "rag_chat.yaml", "workflow-v1")

        sync_templates(source, dest)

        assert (dest / "base" / "chat.yaml").read_text() == "base-v1"
        assert (dest / "workflows" / "rag_chat.yaml").read_text() == "workflow-v1"

    def test_base_is_always_overwritten(self, tmp_path):
        source = tmp_path / "source"
        dest = tmp_path / "dest"
        _write(source / "base", "chat.yaml", "base-v2")
        _write(dest / "base", "chat.yaml", "stale-base")

        sync_templates(source, dest)

        assert (dest / "base" / "chat.yaml").read_text() == "base-v2"

    def test_workflows_are_seeded_only_once_admin_edits_survive(self, tmp_path):
        # The whole point of this function: an admin's in-UI edit to a
        # workflow YAML (persisted on the app_data volume) must not be
        # clobbered by the shipped default on the next restart/redeploy.
        source = tmp_path / "source"
        dest = tmp_path / "dest"
        _write(source / "workflows", "rag_chat.yaml", "shipped-default")
        _write(dest / "workflows", "rag_chat.yaml", "admin-edited-version")

        sync_templates(source, dest)

        assert (dest / "workflows" / "rag_chat.yaml").read_text() == "admin-edited-version"

    def test_new_workflow_files_are_still_added_when_missing(self, tmp_path):
        # A workflow file that doesn't exist yet on the dest volume (e.g. a
        # new default workflow shipped in a later release) still gets seeded,
        # even though existing ones aren't overwritten.
        source = tmp_path / "source"
        dest = tmp_path / "dest"
        _write(source / "workflows", "rag_chat.yaml", "existing")
        _write(source / "workflows", "generate.yaml", "brand-new")
        _write(dest / "workflows", "rag_chat.yaml", "admin-edited")

        sync_templates(source, dest)

        assert (dest / "workflows" / "rag_chat.yaml").read_text() == "admin-edited"
        assert (dest / "workflows" / "generate.yaml").read_text() == "brand-new"

    def test_ignores_non_yaml_files(self, tmp_path):
        source = tmp_path / "source"
        dest = tmp_path / "dest"
        _write(source / "base", "chat.yaml", "yaml-content")
        _write(source / "base", "README.md", "not-a-workflow")

        sync_templates(source, dest)

        assert (dest / "base" / "chat.yaml").exists()
        assert not (dest / "base" / "README.md").exists()
