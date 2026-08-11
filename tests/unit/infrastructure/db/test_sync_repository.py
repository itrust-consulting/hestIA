from __future__ import annotations

import pytest

from hestia.infrastructure.db.sync_repository import SyncManifestRepository
from hestia.infrastructure.db.user_repository import create_sqlite_connection


@pytest.fixture
def repo():
    get_conn, close, lock = create_sqlite_connection(":memory:")
    r = SyncManifestRepository(get_conn=get_conn, db_lock=lock)
    r.initialize()
    return r


class TestSyncManifestRepository:

    def test_get_manifest_empty_when_no_entries(self, repo):
        assert repo.get_manifest("col1", "sync1") == {}

    def test_upsert_then_get_manifest(self, repo):
        repo.upsert_entry("col1", "sync1", "docs/a.md", "hash-a", 100)
        repo.upsert_entry("col1", "sync1", "docs/b.md", "hash-b", 100)
        assert repo.get_manifest("col1", "sync1") == {
            "docs/a.md": "hash-a",
            "docs/b.md": "hash-b",
        }

    def test_upsert_overwrites_existing_hash(self, repo):
        repo.upsert_entry("col1", "sync1", "docs/a.md", "hash-old", 100)
        repo.upsert_entry("col1", "sync1", "docs/a.md", "hash-new", 200)
        assert repo.get_manifest("col1", "sync1") == {"docs/a.md": "hash-new"}

    def test_scoped_by_collection_and_sync_id(self, repo):
        repo.upsert_entry("col1", "sync1", "docs/a.md", "hash-a", 100)
        repo.upsert_entry("col1", "sync2", "docs/a.md", "hash-other-sync", 100)
        repo.upsert_entry("col2", "sync1", "docs/a.md", "hash-other-col", 100)
        assert repo.get_manifest("col1", "sync1") == {"docs/a.md": "hash-a"}

    def test_delete_entry_removes_regardless_of_sync_id(self, repo):
        repo.upsert_entry("col1", "sync1", "docs/a.md", "hash-a", 100)
        repo.delete_entry("col1", "docs/a.md")
        assert repo.get_manifest("col1", "sync1") == {}

    def test_get_hash_for_source_returns_none_when_untracked(self, repo):
        assert repo.get_hash_for_source("col1", "docs/a.md") is None

    def test_get_hash_for_source_finds_hash_regardless_of_sync_id(self, repo):
        repo.upsert_entry("col1", "sync1", "docs/a.md", "hash-a", 100)
        assert repo.get_hash_for_source("col1", "docs/a.md") == "hash-a"


class TestContentOwners:

    def test_get_owner_none_when_unclaimed(self, repo):
        assert repo.get_owner("col1", "hash-a") is None

    def test_claim_owner_first_caller_wins(self, repo):
        owner = repo.claim_owner("col1", "hash-a", "docs/a.md")
        assert owner == "docs/a.md"
        assert repo.get_owner("col1", "hash-a") == "docs/a.md"

    def test_claim_owner_second_caller_loses_race(self, repo):
        repo.claim_owner("col1", "hash-a", "docs/a.md")
        owner = repo.claim_owner("col1", "hash-a", "docs/b.md")
        assert owner == "docs/a.md"
        assert repo.get_owner("col1", "hash-a") == "docs/a.md"

    def test_ownership_scoped_per_collection(self, repo):
        repo.claim_owner("col1", "hash-a", "docs/a.md")
        owner = repo.claim_owner("col2", "hash-a", "docs/b.md")
        assert owner == "docs/b.md"

    def test_get_references_lists_all_source_uris_for_hash_across_sync_ids(self, repo):
        repo.upsert_entry("col1", "sync1", "docs/a.md", "hash-a", 100)
        repo.upsert_entry("col1", "sync2", "docs/b.md", "hash-a", 200)
        repo.upsert_entry("col1", "sync1", "docs/c.md", "hash-other", 100)
        assert repo.get_references("col1", "hash-a") == ["docs/a.md", "docs/b.md"]

    def test_reassign_owner_updates_owner(self, repo):
        repo.claim_owner("col1", "hash-a", "docs/a.md")
        repo.reassign_owner("col1", "hash-a", "docs/b.md")
        assert repo.get_owner("col1", "hash-a") == "docs/b.md"

    def test_remove_owner_clears_entry(self, repo):
        repo.claim_owner("col1", "hash-a", "docs/a.md")
        repo.remove_owner("col1", "hash-a")
        assert repo.get_owner("col1", "hash-a") is None


class TestSyncRuns:

    def test_get_last_synced_at_none_when_never_synced(self, repo):
        assert repo.get_last_synced_at("col1", "sync1") is None

    def test_mark_synced_then_get(self, repo):
        repo.mark_synced("col1", "sync1", 1000)
        assert repo.get_last_synced_at("col1", "sync1") == 1000

    def test_mark_synced_overwrites_previous_time(self, repo):
        repo.mark_synced("col1", "sync1", 1000)
        repo.mark_synced("col1", "sync1", 2000)
        assert repo.get_last_synced_at("col1", "sync1") == 2000

    def test_scoped_per_collection_and_sync_id(self, repo):
        repo.mark_synced("col1", "sync1", 1000)
        assert repo.get_last_synced_at("col1", "sync2") is None
        assert repo.get_last_synced_at("col2", "sync1") is None


class TestDeleteCollectionData:

    def test_clears_sync_manifest(self, repo):
        repo.upsert_entry("col1", "sync1", "docs/a.md", "hash-a", 100)
        repo.delete_collection("col1")
        assert repo.get_manifest("col1", "sync1") == {}

    def test_clears_content_owners(self, repo):
        repo.claim_owner("col1", "hash-a", "docs/a.md")
        repo.delete_collection("col1")
        assert repo.get_owner("col1", "hash-a") is None

    def test_clears_sync_runs(self, repo):
        repo.mark_synced("col1", "sync1", 1000)
        repo.delete_collection("col1")
        assert repo.get_last_synced_at("col1", "sync1") is None

    def test_does_not_affect_other_collections(self, repo):
        repo.upsert_entry("col1", "sync1", "docs/a.md", "hash-a", 100)
        repo.claim_owner("col1", "hash-a", "docs/a.md")
        repo.mark_synced("col1", "sync1", 1000)
        repo.upsert_entry("col2", "sync1", "docs/a.md", "hash-a", 100)
        repo.claim_owner("col2", "hash-a", "docs/a.md")
        repo.mark_synced("col2", "sync1", 1000)

        repo.delete_collection("col1")

        assert repo.get_manifest("col2", "sync1") == {"docs/a.md": "hash-a"}
        assert repo.get_owner("col2", "hash-a") == "docs/a.md"
        assert repo.get_last_synced_at("col2", "sync1") == 1000
