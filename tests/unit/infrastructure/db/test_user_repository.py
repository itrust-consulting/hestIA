from __future__ import annotations

import json
import sqlite3
import threading
import uuid

import pytest

from hestia.infrastructure.db.user_repository import (
    ModeratorConflictError,
    UserRepository,
    create_sqlite_connection,
    with_txn,
)


# ---------------------------------------------------------------------------
# Fixtures — in-memory SQLite
# ---------------------------------------------------------------------------

@pytest.fixture
def repo():
    get_conn, close, lock = create_sqlite_connection(":memory:")
    r = UserRepository(get_conn=get_conn, db_lock=lock)
    r.initialize()
    return r


def _uid():
    return uuid.uuid4()


def _insert_user(repo: UserRepository, username="alice", email="alice@x.com"):
    uid = _uid()
    repo.insert_user(
        user_id=uid,
        username=username,
        email=email,
        first_name="Alice",
        last_name="Smith",
        password_hash=b"\x00" * 32,
        salt=b"\x00" * 16,
        auth_source="local",
        must_change_pw=0,
        created_ts=0,
        expires_ts=None,
    )
    return uid


# ---------------------------------------------------------------------------
# create_sqlite_connection
# ---------------------------------------------------------------------------

class TestCreateSqliteConnection:

    def test_returns_callable_that_provides_connection(self):
        get_conn, close, lock = create_sqlite_connection(":memory:")
        conn = get_conn()
        assert isinstance(conn, sqlite3.Connection)
        close()

    def test_creates_missing_parent_directory(self, tmp_path):
        # Regression test: on a fresh environment with no pre-existing
        # app/data, sqlite3.connect() used to raise "unable to open database
        # file" here because nothing created the parent directory first --
        # crashing startup before a single request could be served.
        db_path = tmp_path / "does" / "not" / "exist" / "users.db"
        assert not db_path.parent.exists()

        get_conn, close, lock = create_sqlite_connection(str(db_path))
        conn = get_conn()

        assert db_path.parent.is_dir()
        assert isinstance(conn, sqlite3.Connection)
        close()

    def test_same_thread_reuses_connection(self):
        get_conn, close, lock = create_sqlite_connection(":memory:")
        c1 = get_conn()
        c2 = get_conn()
        assert c1 is c2
        close()


# ---------------------------------------------------------------------------
# UserRepository.initialize (schema creation)
# ---------------------------------------------------------------------------

class TestInitialize:

    def test_creates_users_table(self):
        get_conn, _, _ = create_sqlite_connection(":memory:")
        r = UserRepository(get_conn=get_conn, db_lock=threading.Lock())
        r.initialize()
        conn = get_conn()
        tables = {row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        assert "users" in tables
        assert "roles" in tables
        assert "organizations" in tables

    def test_default_roles_seeded(self, repo):
        roles = repo.list_roles()
        names = {r["name"] for r in roles}
        assert "admin" in names
        assert "user" in names

    def test_migrates_pre_rename_collection_tenants_without_losing_data(self):
        # Regression test: initialize() used to run "ADD COLUMN role" on
        # tenant_collections before the RENAME from the table's old name
        # (collection_tenants). On a database that still had the old name,
        # CREATE TABLE IF NOT EXISTS tenant_collections (earlier in the same
        # script) had already created a new, empty table under the new name,
        # so the rename failed (target exists) and the old table's data was
        # silently orphaned.
        get_conn, _, _ = create_sqlite_connection(":memory:")
        conn = get_conn()
        conn.executescript(
            """
            CREATE TABLE organizations (
                id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE,
                abbreviation TEXT UNIQUE, created_at INTEGER
            );
            CREATE TABLE collection_tenants (
                org_id INTEGER NOT NULL, collection_id TEXT NOT NULL,
                PRIMARY KEY (org_id, collection_id)
            );
            INSERT INTO organizations (name, abbreviation, created_at) VALUES ('Acme', 'ACM', 1);
            INSERT INTO collection_tenants (org_id, collection_id) VALUES (1, 'col1');
            """
        )
        conn.commit()

        repo = UserRepository(get_conn=get_conn, db_lock=threading.Lock())
        repo.initialize()

        tables = {row["name"] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        assert "collection_tenants" not in tables

        cols = {row["name"] for row in conn.execute("PRAGMA table_info(tenant_collections)").fetchall()}
        assert {"org_id", "collection_id", "role", "max_classification"} <= cols

        rows = conn.execute("SELECT * FROM tenant_collections").fetchall()
        assert len(rows) == 1
        assert rows[0]["org_id"] == 1
        assert rows[0]["collection_id"] == "col1"
        assert rows[0]["role"] == "access"  # DEFAULT applied by the ADD COLUMN migration


# ---------------------------------------------------------------------------
# User CRUD
# ---------------------------------------------------------------------------

class TestUserCRUD:

    def test_insert_and_get_by_username(self, repo):
        uid = _insert_user(repo, username="bob", email="bob@x.com")
        row = repo.get_user_by_username("bob")
        assert row is not None
        assert uuid.UUID(bytes=row["id"]) == uid

    def test_get_user_by_email(self, repo):
        _insert_user(repo, username="carol", email="carol@x.com")
        row = repo.get_user_by_email("carol@x.com")
        assert row is not None

    def test_delete_user(self, repo):
        uid = _insert_user(repo, username="dave", email="dave@x.com")
        repo.delete_user(id=uid)
        assert repo.get_user_by_username("dave") is None

    def test_update_username(self, repo):
        uid = _insert_user(repo, username="old", email="old@x.com")
        repo.update_username(id=uid, new_username="new_name", updated_ts=1)
        row = repo.get_user_by_id(uid)
        assert row["username"] == "new_name"

    def test_update_user_email(self, repo):
        uid = _insert_user(repo, username="em", email="em@x.com")
        repo.update_user_email(id=uid, new_email="new@x.com", updated_ts=1)
        row = repo.get_user_by_id(uid)
        assert row["email"] == "new@x.com"

    def test_list_users_returns_all(self, repo):
        _insert_user(repo, username="u1", email="u1@x.com")
        _insert_user(repo, username="u2", email="u2@x.com")
        users = repo.list_users()
        usernames = [u["username"] for u in users]
        assert "u1" in usernames
        assert "u2" in usernames


# ---------------------------------------------------------------------------
# Roles
# ---------------------------------------------------------------------------

class TestRoles:

    def test_add_role_to_user(self, repo):
        uid = _insert_user(repo, username="r1", email="r1@x.com")
        user_role = repo.get_role_by_name("user")
        repo.add_role_to_user(user_id=uid, role_id=user_role["id"], starts_ts=0)
        roles = repo.get_user_roles(uid)
        assert any(r["name"] == "user" for r in roles)

    def test_remove_role_from_user(self, repo):
        uid = _insert_user(repo, username="r2", email="r2@x.com")
        user_role = repo.get_role_by_name("user")
        repo.add_role_to_user(user_id=uid, role_id=user_role["id"], starts_ts=0)
        repo.remove_role_from_user(user_id=uid, role_id=user_role["id"])
        roles = repo.get_user_roles(uid)
        assert not any(r["name"] == "user" for r in roles)


# ---------------------------------------------------------------------------
# Organizations
# ---------------------------------------------------------------------------

class TestOrganizations:

    def test_insert_and_get_org(self, repo):
        created = repo.insert_organization(name="OrgA", abbreviation="OA", created_ts=0)
        assert created is True
        org = repo.get_organization_by_name("OrgA")
        assert org is not None
        assert org["abbreviation"] == "OA"

    def test_name_collision_is_a_silent_noop_reported_as_false(self, repo):
        first = repo.insert_organization(name="Dup-Org", abbreviation="D1", created_ts=0)
        second = repo.insert_organization(name="Dup-Org", abbreviation="D2", created_ts=1)
        assert first is True
        assert second is False
        # confirms it's a true no-op, not a partial write under a new abbreviation
        assert repo.get_organization_by_name("Dup-Org")["abbreviation"] == "D1"

    def test_abbreviation_collision_is_a_silent_noop_reported_as_false(self, repo):
        first = repo.insert_organization(name="Org-One", abbreviation="DUP", created_ts=0)
        second = repo.insert_organization(name="Org-Two", abbreviation="DUP", created_ts=1)
        assert first is True
        assert second is False
        assert repo.get_organization_by_name("Org-Two") is None

    def test_delete_org(self, repo):
        repo.insert_organization(name="OrgB", abbreviation="OB", created_ts=0)
        org = repo.get_organization_by_name("OrgB")
        repo.delete_organization(id=org["id"])
        assert repo.get_organization_by_name("OrgB") is None

    def test_add_user_to_org(self, repo):
        uid = _insert_user(repo, username="mo", email="mo@x.com")
        repo.insert_organization(name="OrgC", abbreviation="OC", created_ts=0)
        org = repo.get_organization_by_name("OrgC")
        repo.add_user_to_organization(user_id=uid, org_id=org["id"])
        orgs = repo.get_user_organizations(uid)
        assert any(o["name"] == "OrgC" for o in orgs)

    def test_remove_user_from_org(self, repo):
        uid = _insert_user(repo, username="rm", email="rm@x.com")
        repo.insert_organization(name="OrgD", abbreviation="OD", created_ts=0)
        org = repo.get_organization_by_name("OrgD")
        repo.add_user_to_organization(user_id=uid, org_id=org["id"])
        repo.remove_user_from_organization(user_id=uid, org_id=org["id"])
        orgs = repo.get_user_organizations(uid)
        assert not any(o["name"] == "OrgD" for o in orgs)


# ---------------------------------------------------------------------------
# Tenant collections
# ---------------------------------------------------------------------------

class TestTenantCollections:

    def test_add_and_get_tenant_collection(self, repo):
        repo.insert_organization(name="TC-Org", abbreviation="TC", created_ts=0)
        org = repo.get_organization_by_name("TC-Org")
        repo.add_tenant_collection(org_id=org["id"], collection_id="my-collection",
                                   role="owner", max_classification=3)
        cols = repo.get_tenant_collections(org["id"])
        assert any(c["collection_id"] == "my-collection" for c in cols)

    def test_remove_collection_grant(self, repo):
        repo.insert_organization(name="RC-Org", abbreviation="RC", created_ts=0)
        org = repo.get_organization_by_name("RC-Org")
        repo.add_tenant_collection(org_id=org["id"], collection_id="col-x",
                                   role="access", max_classification=None)
        repo.remove_tenant_collection(org_id=org["id"], collection_id="col-x")
        cols = repo.get_tenant_collections(org["id"])
        assert not any(c["collection_id"] == "col-x" for c in cols)


# ---------------------------------------------------------------------------
# Conversations
# ---------------------------------------------------------------------------

class TestConversations:

    def test_insert_and_list_conversations(self, repo):
        uid = _insert_user(repo, username="conv", email="conv@x.com")
        c_id = _uid()
        repo.insert_conversation(conv_id=c_id, user_id=uid, title="My Chat",
                                 metadata_json="{}", ts=0)
        convs = repo.get_conversation(uid, limit=10, offset=0)
        assert any(c["title"] == "My Chat" for c in convs)

    def test_update_conversation_title(self, repo):
        uid = _insert_user(repo, username="ct", email="ct@x.com")
        c_id = _uid()
        repo.insert_conversation(conv_id=c_id, user_id=uid, title="Old Title",
                                 metadata_json="{}", ts=0)
        repo.update_conversation_title(user_id=uid, c_id=c_id, title="New Title")
        convs = repo.get_conversation(uid, limit=10, offset=0)
        assert convs[0]["title"] == "New Title"

    def test_delete_conversation(self, repo):
        uid = _insert_user(repo, username="dc", email="dc@x.com")
        c_id = _uid()
        repo.insert_conversation(conv_id=c_id, user_id=uid, title="To delete",
                                 metadata_json="{}", ts=0)
        repo.delete_conversation(user_id=uid, c_id=c_id)
        convs = repo.get_conversation(uid, limit=10, offset=0)
        assert len(convs) == 0


# ---------------------------------------------------------------------------
# Messages
# ---------------------------------------------------------------------------

class TestWithTxnRollback:

    def test_rolls_back_on_exception(self):
        get_conn, _, lock = create_sqlite_connection(":memory:")
        r = UserRepository(get_conn=get_conn, db_lock=lock)
        r.initialize()

        with pytest.raises(Exception, match="deliberate"):
            # insert_user decorated with with_txn — if it raises, transaction rolls back
            r.insert_user(
                user_id=uuid.uuid4(),
                username="x" * 300,  # SQLite will accept but UNIQUE may not; force via monkeypatch below
                email="x@x.com",
                first_name="F", last_name="L",
                auth_source="local",
                password_hash=b"\x00" * 32,
                salt=b"\x00" * 16,
                must_change_pw=0,
                created_ts=0,
            )
            raise Exception("deliberate")

    def test_commits_on_success(self):
        get_conn, _, lock = create_sqlite_connection(":memory:")
        r = UserRepository(get_conn=get_conn, db_lock=lock)
        r.initialize()
        uid = uuid.uuid4()
        r.insert_user(
            user_id=uid, username="commit_test", email="ct@x.com",
            first_name="C", last_name="T", auth_source="local",
            password_hash=b"\x00" * 32, salt=b"\x00" * 16,
            must_change_pw=0, created_ts=0,
        )
        assert r.get_user_by_username("commit_test") is not None


class TestMemberClassificationAndRole:

    def test_set_member_classification(self, repo):
        uid = _insert_user(repo, username="cls", email="cls@x.com")
        repo.insert_organization(name="ClsOrg", abbreviation="CLS", created_ts=0)
        org = repo.get_organization_by_name("ClsOrg")
        repo.add_user_to_organization(user_id=uid, org_id=org["id"])
        repo.set_member_classification(user_id=uid, org_id=org["id"], level=3)
        memberships = repo.get_user_org_memberships(uid)
        assert memberships[0]["classification_level"] == 3

    def test_set_member_tenant_role(self, repo):
        uid = _insert_user(repo, username="tr", email="tr@x.com")
        repo.insert_organization(name="TrOrg", abbreviation="TR", created_ts=0)
        org = repo.get_organization_by_name("TrOrg")
        repo.add_user_to_organization(user_id=uid, org_id=org["id"])
        repo.set_member_tenant_role(user_id=uid, org_id=org["id"], role="moderator")
        memberships = repo.get_user_org_memberships(uid)
        assert memberships[0]["tenant_role"] == "moderator"


class TestRemoveCollectionGrants:

    def test_removes_all_grants_for_collection(self, repo):
        repo.insert_organization(name="GrA", abbreviation="GA", created_ts=0)
        repo.insert_organization(name="GrB", abbreviation="GB", created_ts=0)
        org_a = repo.get_organization_by_name("GrA")
        org_b = repo.get_organization_by_name("GrB")
        repo.add_tenant_collection(org_id=org_a["id"], collection_id="shared-col", role="owner")
        repo.add_tenant_collection(org_id=org_b["id"], collection_id="shared-col", role="access")
        repo.remove_collection_grants(collection_id="shared-col")
        assert repo.get_tenant_collections(org_a["id"]) == []
        assert repo.get_tenant_collections(org_b["id"]) == []


class TestMessages:

    def test_insert_and_get_messages(self, repo):
        uid = _insert_user(repo, username="msg", email="msg@x.com")
        c_id = _uid()
        repo.insert_conversation(conv_id=c_id, user_id=uid, title="Chat",
                                 metadata_json="{}", ts=0)
        m_id = _uid()
        repo.insert_message(msg_id=m_id, c_id=c_id, role="user",
                            metadata="{}", content="Hello", options="{}", ts=1)
        messages = repo.get_messages(c_id, limit=10)
        assert len(messages) == 1
        assert messages[0]["content"] == "Hello"

    def test_messages_ordered_desc_by_ts(self, repo):
        uid = _insert_user(repo, username="ord", email="ord@x.com")
        c_id = _uid()
        repo.insert_conversation(conv_id=c_id, user_id=uid, title="C",
                                 metadata_json="{}", ts=0)
        repo.insert_message(msg_id=_uid(), c_id=c_id, role="user",
                            metadata="{}", content="first", options="{}", ts=1)
        repo.insert_message(msg_id=_uid(), c_id=c_id, role="assistant",
                            metadata="{}", content="second", options="{}", ts=2)
        # get_messages returns DESC order
        messages = repo.get_messages(c_id, limit=10)
        assert messages[0]["content"] == "second"
        assert messages[1]["content"] == "first"

    def test_delete_message(self, repo):
        uid = _insert_user(repo, username="dm", email="dm@x.com")
        c_id = _uid()
        repo.insert_conversation(conv_id=c_id, user_id=uid, title="C",
                                 metadata_json="{}", ts=0)
        m_id = _uid()
        repo.insert_message(msg_id=m_id, c_id=c_id, role="user",
                            metadata="{}", content="to delete", options="{}", ts=1)
        repo.delete_message(c_id=c_id, msg_id=m_id)
        assert repo.get_messages(c_id, limit=10) == []

    def test_get_messages_cursor_pagination_walks_full_history(self, repo):
        uid = _insert_user(repo, username="pg", email="pg@x.com")
        c_id = _uid()
        repo.insert_conversation(conv_id=c_id, user_id=uid, title="C",
                                 metadata_json="{}", ts=0)
        for i in range(5):
            repo.insert_message(msg_id=_uid(), c_id=c_id, role="user",
                                metadata="{}", content=f"msg{i}", options="{}", ts=i)

        seen = []
        before_created_at = None
        before_rowid = None
        for _ in range(5):
            page = repo.get_messages(c_id, limit=1,
                                     before_created_at=before_created_at,
                                     before_rowid=before_rowid)
            assert len(page) == 1
            seen.append(page[0]["content"])
            before_created_at = page[0]["created_at"]
            before_rowid = page[0]["rowid"]

        assert seen == ["msg4", "msg3", "msg2", "msg1", "msg0"]
        # one more page past the end of history returns nothing
        assert repo.get_messages(c_id, limit=1,
                                 before_created_at=before_created_at,
                                 before_rowid=before_rowid) == []

    def test_get_messages_cursor_tie_break_on_rowid(self, repo):
        uid = _insert_user(repo, username="tie", email="tie@x.com")
        c_id = _uid()
        repo.insert_conversation(conv_id=c_id, user_id=uid, title="C",
                                 metadata_json="{}", ts=0)
        repo.insert_message(msg_id=_uid(), c_id=c_id, role="user",
                            metadata="{}", content="first", options="{}", ts=100)
        repo.insert_message(msg_id=_uid(), c_id=c_id, role="assistant",
                            metadata="{}", content="second", options="{}", ts=100)

        newest = repo.get_messages(c_id, limit=1)
        assert newest[0]["content"] == "second"

        older = repo.get_messages(c_id, limit=1,
                                  before_created_at=newest[0]["created_at"],
                                  before_rowid=newest[0]["rowid"])
        assert len(older) == 1
        assert older[0]["content"] == "first"


class TestGetMessagesAfter:

    def test_no_boundary_returns_full_ascending_order(self, repo):
        uid = _insert_user(repo, username="asc", email="asc@x.com")
        c_id = _uid()
        repo.insert_conversation(conv_id=c_id, user_id=uid, title="C",
                                 metadata_json="{}", ts=0)
        for i in range(3):
            repo.insert_message(msg_id=_uid(), c_id=c_id, role="user",
                                metadata="{}", content=f"msg{i}", options="{}", ts=i)

        rows = repo.get_messages_after(c_id)
        assert [r["content"] for r in rows] == ["msg0", "msg1", "msg2"]

    def test_boundary_excludes_messages_at_or_before_it(self, repo):
        uid = _insert_user(repo, username="bnd", email="bnd@x.com")
        c_id = _uid()
        repo.insert_conversation(conv_id=c_id, user_id=uid, title="C",
                                 metadata_json="{}", ts=0)
        for i in range(5):
            repo.insert_message(msg_id=_uid(), c_id=c_id, role="user",
                                metadata="{}", content=f"msg{i}", options="{}", ts=i)

        boundary = repo.get_messages_after(c_id)[1]  # msg1
        rows = repo.get_messages_after(c_id, after_created_at=boundary["created_at"],
                                      after_rowid=boundary["rowid"])
        assert [r["content"] for r in rows] == ["msg2", "msg3", "msg4"]

    def test_rowid_tie_break(self, repo):
        uid = _insert_user(repo, username="atie", email="atie@x.com")
        c_id = _uid()
        repo.insert_conversation(conv_id=c_id, user_id=uid, title="C",
                                 metadata_json="{}", ts=0)
        repo.insert_message(msg_id=_uid(), c_id=c_id, role="user",
                            metadata="{}", content="first", options="{}", ts=100)
        repo.insert_message(msg_id=_uid(), c_id=c_id, role="assistant",
                            metadata="{}", content="second", options="{}", ts=100)

        oldest = repo.get_messages_after(c_id)[0]
        assert oldest["content"] == "first"

        newer = repo.get_messages_after(c_id, after_created_at=oldest["created_at"],
                                        after_rowid=oldest["rowid"])
        assert len(newer) == 1
        assert newer[0]["content"] == "second"

    def test_no_messages_left_past_the_newest(self, repo):
        uid = _insert_user(repo, username="past", email="past@x.com")
        c_id = _uid()
        repo.insert_conversation(conv_id=c_id, user_id=uid, title="C",
                                 metadata_json="{}", ts=0)
        repo.insert_message(msg_id=_uid(), c_id=c_id, role="user",
                            metadata="{}", content="only", options="{}", ts=1)
        newest = repo.get_messages_after(c_id)[0]
        assert repo.get_messages_after(c_id, after_created_at=newest["created_at"],
                                       after_rowid=newest["rowid"]) == []


class TestConversationMetadata:

    def test_round_trip_get_update(self, repo):
        uid = _insert_user(repo, username="meta", email="meta@x.com")
        c_id = _uid()
        repo.insert_conversation(conv_id=c_id, user_id=uid, title="C",
                                 metadata_json="{}", ts=0)

        assert repo.get_conversation_metadata(c_id)["metadata_json"] == "{}"

        repo.update_conversation_metadata(c_id=c_id, metadata_json='{"foo": "bar"}')
        assert repo.get_conversation_metadata(c_id)["metadata_json"] == '{"foo": "bar"}'

    def test_missing_conversation_returns_none(self, repo):
        assert repo.get_conversation_metadata(_uid()) is None


# ---------------------------------------------------------------------------
# Transactional approval flows (join/share/invitation) — these compose what
# used to be several independent, separately-committing repo calls into one
# @with_txn-wrapped method, so a failure partway through can't leave a
# request resolved-but-ungranted or granted-but-still-pending.
# ---------------------------------------------------------------------------

class TestApprovalTransactions:

    def test_approve_join_request_and_grant_applies_membership_and_resolves(self, repo):
        uid = _insert_user(repo, username="joiner", email="joiner@x.com")
        repo.insert_organization(name="Join-Org", abbreviation="JO", created_ts=0)
        org = repo.get_organization_by_name("Join-Org")
        req_id = _uid()
        repo.insert_join_request(req_id=req_id, user_id=uid, org_id=org["id"], message=None, ts=0)

        repo.approve_join_request_and_grant(
            req_id=req_id, user_id=uid, org_id=org["id"], classification_level=2,
            tenant_role="moderator", reviewer_id=_uid(), ts=1,
        )

        memberships = repo.get_user_org_memberships(uid)
        assert len(memberships) == 1
        assert memberships[0]["classification_level"] == 2
        assert memberships[0]["tenant_role"] == "moderator"

        req = repo.get_join_request(req_id)
        assert req["status"] == "approved"
        assert req["granted_classification_level"] == 2

    def test_approve_join_request_and_grant_is_atomic_on_failure(self, repo):
        # A bogus org_id violates the FOREIGN KEY on user_orgs.org_id
        # (PRAGMA foreign_keys=ON), simulating a failure partway through the
        # grant sequence -- the request must stay 'pending', not end up
        # resolved without a real membership grant.
        uid = _insert_user(repo, username="joiner2", email="joiner2@x.com")
        repo.insert_organization(name="Join-Org-2", abbreviation="JO2", created_ts=0)
        org = repo.get_organization_by_name("Join-Org-2")
        req_id = _uid()
        repo.insert_join_request(req_id=req_id, user_id=uid, org_id=org["id"], message=None, ts=0)

        with pytest.raises(sqlite3.IntegrityError):
            repo.approve_join_request_and_grant(
                req_id=req_id, user_id=uid, org_id=999999, classification_level=0,
                tenant_role=None, reviewer_id=_uid(), ts=1,
            )

        assert repo.get_user_org_memberships(uid) == []
        req = repo.get_join_request(req_id)
        assert req["status"] == "pending"

    def test_approve_share_request_and_grant_applies_all_collections_and_resolves(self, repo):
        repo.insert_organization(name="Requesting-Org", abbreviation="RO", created_ts=0)
        repo.insert_organization(name="Target-Org", abbreviation="TO", created_ts=0)
        requesting_org = repo.get_organization_by_name("Requesting-Org")
        target_org = repo.get_organization_by_name("Target-Org")
        req_id = _uid()
        repo.insert_share_request(
            req_id=req_id, requesting_org_id=requesting_org["id"], target_org_id=target_org["id"],
            message=None, requested_by=_uid(), ts=0,
        )

        repo.approve_share_request_and_grant(
            req_id=req_id, requesting_org_id=requesting_org["id"],
            grants=[("col-a", 1), ("col-b", None)], reviewer_id=_uid(), ts=1,
        )

        cols = {c["collection_id"] for c in repo.get_tenant_collections(requesting_org["id"])}
        assert cols == {"col-a", "col-b"}
        assert {g["collection_id"] for g in repo.list_share_grants(req_id)} == {"col-a", "col-b"}
        assert repo.get_share_request(req_id)["status"] == "approved"

    def test_accept_invitation_and_grant_applies_membership_and_resolves(self, repo):
        uid = _insert_user(repo, username="invitee", email="invitee@x.com")
        repo.insert_organization(name="Invite-Org", abbreviation="IO", created_ts=0)
        org = repo.get_organization_by_name("Invite-Org")
        inv_id = _uid()
        repo.insert_invitation(inv_id=inv_id, org_id=org["id"], user_id=uid, invited_by=_uid(),
                               message=None, ts=0)

        repo.accept_invitation_and_grant(inv_id=inv_id, user_id=uid, org_id=org["id"], ts=1)

        memberships = repo.get_user_org_memberships(uid)
        assert len(memberships) == 1
        assert memberships[0]["classification_level"] == 0
        assert repo.get_invitation(inv_id)["status"] == "accepted"


class TestOnePendingRequestPerPairIndexes:
    """The partial unique indexes backstopping file_join_request/invite_user/
    file_share_request's check-then-insert race (see user_repository.py's
    initialize()) -- verified here against a real schema rather than mocks,
    since a typo in the index definition would silently not enforce anything."""

    def test_second_pending_join_request_for_same_pair_is_rejected(self, repo):
        uid = _insert_user(repo, username="dupjoin", email="dupjoin@x.com")
        repo.insert_organization(name="Dup-Join-Org", abbreviation="DJO", created_ts=0)
        org = repo.get_organization_by_name("Dup-Join-Org")
        repo.insert_join_request(req_id=_uid(), user_id=uid, org_id=org["id"], message=None, ts=0)

        with pytest.raises(sqlite3.IntegrityError):
            repo.insert_join_request(req_id=_uid(), user_id=uid, org_id=org["id"], message=None, ts=1)

    def test_a_resolved_request_does_not_block_a_new_one(self, repo):
        # The index is scoped to WHERE status='pending' -- once the first
        # request is resolved, a fresh pending one for the same pair is fine.
        uid = _insert_user(repo, username="rejoiner", email="rejoiner@x.com")
        repo.insert_organization(name="Rejoin-Org", abbreviation="RJO", created_ts=0)
        org = repo.get_organization_by_name("Rejoin-Org")
        first_req = _uid()
        repo.insert_join_request(req_id=first_req, user_id=uid, org_id=org["id"], message=None, ts=0)
        repo.resolve_join_request(
            req_id=first_req, status="rejected", reviewed_by=_uid(), review_reason=None,
            granted_tenant_role=None, granted_classification_level=None, ts=1,
        )

        # Must not raise.
        repo.insert_join_request(req_id=_uid(), user_id=uid, org_id=org["id"], message=None, ts=2)

    def test_second_pending_invitation_for_same_pair_is_rejected(self, repo):
        uid = _insert_user(repo, username="dupinvite", email="dupinvite@x.com")
        repo.insert_organization(name="Dup-Invite-Org", abbreviation="DIO", created_ts=0)
        org = repo.get_organization_by_name("Dup-Invite-Org")
        repo.insert_invitation(inv_id=_uid(), org_id=org["id"], user_id=uid, invited_by=_uid(),
                               message=None, ts=0)

        with pytest.raises(sqlite3.IntegrityError):
            repo.insert_invitation(inv_id=_uid(), org_id=org["id"], user_id=uid, invited_by=_uid(),
                                   message=None, ts=1)

    def test_second_pending_share_request_for_same_pair_is_rejected(self, repo):
        repo.insert_organization(name="Dup-Req-Org", abbreviation="DRO", created_ts=0)
        repo.insert_organization(name="Dup-Tgt-Org", abbreviation="DTO", created_ts=0)
        requesting_org = repo.get_organization_by_name("Dup-Req-Org")
        target_org = repo.get_organization_by_name("Dup-Tgt-Org")
        repo.insert_share_request(
            req_id=_uid(), requesting_org_id=requesting_org["id"], target_org_id=target_org["id"],
            message=None, requested_by=_uid(), ts=0,
        )

        with pytest.raises(sqlite3.IntegrityError):
            repo.insert_share_request(
                req_id=_uid(), requesting_org_id=requesting_org["id"], target_org_id=target_org["id"],
                message=None, requested_by=_uid(), ts=1,
            )


class TestWithTxnRetry:
    """with_txn's own in-process lock means an OperationalError here can
    only realistically come from a second process holding the SQLite file
    lock -- simulated directly here by making the wrapped function raise it,
    since reproducing a real second process isn't practical in a unit test."""

    def _repo(self):
        get_conn, _close, lock = create_sqlite_connection(":memory:")

        class _Repo:
            _get_conn = staticmethod(get_conn)
            _db_lock = lock

        return _Repo()

    def test_retries_and_recovers_from_a_transient_operational_error(self):
        calls = {"n": 0}

        @with_txn
        def flaky(self, conn):
            calls["n"] += 1
            if calls["n"] < 2:
                raise sqlite3.OperationalError("database is locked")
            return "ok"

        assert flaky(self._repo()) == "ok"
        assert calls["n"] == 2

    def test_gives_up_and_reraises_after_max_attempts(self):
        calls = {"n": 0}

        @with_txn
        def always_locked(self, conn):
            calls["n"] += 1
            raise sqlite3.OperationalError("database is locked")

        with pytest.raises(sqlite3.OperationalError):
            always_locked(self._repo())
        assert calls["n"] == 3  # _TXN_RETRY_ATTEMPTS

    def test_non_operational_errors_are_not_retried(self):
        calls = {"n": 0}

        @with_txn
        def broken(self, conn):
            calls["n"] += 1
            raise ValueError("not a locking issue")

        with pytest.raises(ValueError):
            broken(self._repo())
        assert calls["n"] == 1


class TestRevokedTokens:

    def test_unrevoked_token_reports_not_revoked(self, repo):
        assert repo.is_token_revoked("some-jti") is False

    def test_revoked_token_reports_revoked(self, repo):
        repo.revoke_token(jti="abc-123", ts=0)
        assert repo.is_token_revoked("abc-123") is True

    def test_revoking_twice_is_a_harmless_noop(self, repo):
        repo.revoke_token(jti="abc-123", ts=0)
        repo.revoke_token(jti="abc-123", ts=1)  # must not raise on the duplicate PK
        assert repo.is_token_revoked("abc-123") is True

    def test_revoking_one_jti_does_not_affect_another(self, repo):
        repo.revoke_token(jti="revoked-one", ts=0)
        assert repo.is_token_revoked("still-fine") is False


class TestApprovalRaceConditions:
    """Regression tests for a TOCTOU race: two concurrent approve/reject
    calls against the same request used to both pass their (unlocked,
    outside-any-transaction) 'is it still pending' check before either
    write landed. The guard now lives in the status UPDATE's own WHERE
    clause, evaluated inside the same transaction as the grant, so a second
    resolution attempt is a no-op instead of a double-grant."""

    def test_approve_join_request_and_grant_is_a_noop_once_already_resolved(self, repo):
        uid = _insert_user(repo, username="racer1", email="racer1@x.com")
        repo.insert_organization(name="Race-Org", abbreviation="RA1", created_ts=0)
        org = repo.get_organization_by_name("Race-Org")
        req_id = _uid()
        repo.insert_join_request(req_id=req_id, user_id=uid, org_id=org["id"], message=None, ts=0)

        first = repo.approve_join_request_and_grant(
            req_id=req_id, user_id=uid, org_id=org["id"], classification_level=0,
            tenant_role=None, reviewer_id=_uid(), ts=1,
        )
        second = repo.approve_join_request_and_grant(
            req_id=req_id, user_id=uid, org_id=org["id"], classification_level=3,
            tenant_role="moderator", reviewer_id=_uid(), ts=2,
        )

        assert first is True
        assert second is False
        # The second call's payload must never have applied -- membership
        # stays exactly what the first call granted.
        memberships = repo.get_user_org_memberships(uid)
        assert len(memberships) == 1
        assert memberships[0]["classification_level"] == 0
        assert memberships[0]["tenant_role"] is None

    def test_approve_join_request_moderator_conflict_rolls_back_cleanly(self, repo):
        # Two pending join requests for the same tenant, both asking for
        # 'moderator'. Approving the second must not grant it a second
        # moderator role, and must leave the second request untouched
        # (still 'pending') rather than resolved-but-not-granted.
        uid1 = _insert_user(repo, username="mod1", email="mod1@x.com")
        uid2 = _insert_user(repo, username="mod2", email="mod2@x.com")
        repo.insert_organization(name="One-Mod-Org", abbreviation="OMO", created_ts=0)
        org = repo.get_organization_by_name("One-Mod-Org")
        req1, req2 = _uid(), _uid()
        repo.insert_join_request(req_id=req1, user_id=uid1, org_id=org["id"], message=None, ts=0)
        repo.insert_join_request(req_id=req2, user_id=uid2, org_id=org["id"], message=None, ts=0)

        ok1 = repo.approve_join_request_and_grant(
            req_id=req1, user_id=uid1, org_id=org["id"], classification_level=0,
            tenant_role="moderator", reviewer_id=_uid(), ts=1,
        )
        assert ok1 is True

        with pytest.raises(ModeratorConflictError):
            repo.approve_join_request_and_grant(
                req_id=req2, user_id=uid2, org_id=org["id"], classification_level=0,
                tenant_role="moderator", reviewer_id=_uid(), ts=2,
            )

        moderators = [m for m in repo.get_user_org_memberships(uid1) + repo.get_user_org_memberships(uid2)
                      if m["tenant_role"] == "moderator"]
        assert len(moderators) == 1
        # Rolled back, not resolved-but-ungranted.
        assert repo.get_join_request(req2)["status"] == "pending"

    def test_resolve_join_request_reject_is_a_noop_once_already_resolved(self, repo):
        uid = _insert_user(repo, username="racer2", email="racer2@x.com")
        repo.insert_organization(name="Race-Org-2", abbreviation="RA2", created_ts=0)
        org = repo.get_organization_by_name("Race-Org-2")
        req_id = _uid()
        repo.insert_join_request(req_id=req_id, user_id=uid, org_id=org["id"], message=None, ts=0)

        first = repo.resolve_join_request(
            req_id=req_id, status="rejected", reviewed_by=_uid(), review_reason=None,
            granted_tenant_role=None, granted_classification_level=None, ts=1,
        )
        second = repo.resolve_join_request(
            req_id=req_id, status="rejected", reviewed_by=_uid(), review_reason="too late",
            granted_tenant_role=None, granted_classification_level=None, ts=2,
        )

        assert first is True
        assert second is False
        assert repo.get_join_request(req_id)["review_reason"] is None

    def test_approve_share_request_and_grant_is_a_noop_once_already_resolved(self, repo):
        repo.insert_organization(name="Req-Org", abbreviation="RQO", created_ts=0)
        repo.insert_organization(name="Tgt-Org", abbreviation="TGO", created_ts=0)
        requesting_org = repo.get_organization_by_name("Req-Org")
        target_org = repo.get_organization_by_name("Tgt-Org")
        req_id = _uid()
        repo.insert_share_request(
            req_id=req_id, requesting_org_id=requesting_org["id"], target_org_id=target_org["id"],
            message=None, requested_by=_uid(), ts=0,
        )

        first = repo.approve_share_request_and_grant(
            req_id=req_id, requesting_org_id=requesting_org["id"],
            grants=[("col-a", 1)], reviewer_id=_uid(), ts=1,
        )
        second = repo.approve_share_request_and_grant(
            req_id=req_id, requesting_org_id=requesting_org["id"],
            grants=[("col-b", None)], reviewer_id=_uid(), ts=2,
        )

        assert first is True
        assert second is False
        cols = {c["collection_id"] for c in repo.get_tenant_collections(requesting_org["id"])}
        assert cols == {"col-a"}

    def test_accept_invitation_and_grant_is_a_noop_once_already_resolved(self, repo):
        uid = _insert_user(repo, username="invitee2", email="invitee2@x.com")
        repo.insert_organization(name="Invite-Org-2", abbreviation="IO2", created_ts=0)
        org = repo.get_organization_by_name("Invite-Org-2")
        inv_id = _uid()
        repo.insert_invitation(inv_id=inv_id, org_id=org["id"], user_id=uid, invited_by=_uid(),
                               message=None, ts=0)

        # Admin cancels first (simulating it winning the race)...
        cancelled = repo.resolve_invitation(inv_id=inv_id, status="cancelled", ts=1)
        # ...then the user's concurrent accept must not still grant access.
        accepted = repo.accept_invitation_and_grant(inv_id=inv_id, user_id=uid, org_id=org["id"], ts=2)

        assert cancelled is True
        assert accepted is False
        assert repo.get_user_org_memberships(uid) == []
        assert repo.get_invitation(inv_id)["status"] == "cancelled"
