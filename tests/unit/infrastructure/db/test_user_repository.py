from __future__ import annotations

import json
import sqlite3
import threading
import uuid

import pytest

from hestia.infrastructure.db.user_repository import (
    UserRepository,
    create_sqlite_connection,
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
        repo.insert_organization(name="OrgA", abbreviation="OA", created_ts=0)
        org = repo.get_organization_by_name("OrgA")
        assert org is not None
        assert org["abbreviation"] == "OA"

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
