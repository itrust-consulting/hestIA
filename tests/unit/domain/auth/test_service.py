from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest

from hestia.domain.auth.models import AuthResult
from hestia.domain.auth.users import UserService
from hestia.domain.auth.service import AuthenticationService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_repo():
    return MagicMock()


@pytest.fixture
def user_service(mock_repo):
    return UserService(repo=mock_repo, password_min_length=8)


@pytest.fixture
def mock_user_service():
    svc = MagicMock()
    svc.repo = MagicMock()
    return svc


@pytest.fixture
def auth_service(mock_user_service):
    return AuthenticationService(local=mock_user_service)


# ---------------------------------------------------------------------------
# UserService._hash_password / _verify_password
# ---------------------------------------------------------------------------

class TestPasswordHashing:

    def test_hash_is_deterministic(self, user_service):
        salt = b"0123456789abcdef"
        h1 = user_service._hash_password("password", salt)
        h2 = user_service._hash_password("password", salt)
        assert h1 == h2

    def test_different_passwords_differ(self, user_service):
        salt = b"0123456789abcdef"
        h1 = user_service._hash_password("password1", salt)
        h2 = user_service._hash_password("password2", salt)
        assert h1 != h2

    def test_different_salts_differ(self, user_service):
        h1 = user_service._hash_password("password", b"salt1" + b"\x00" * 11)
        h2 = user_service._hash_password("password", b"salt2" + b"\x00" * 11)
        assert h1 != h2

    def test_verify_returns_true_for_correct(self, user_service):
        salt = b"0123456789abcdef"
        h = user_service._hash_password("correct", salt)
        assert user_service._verify_password("correct", salt, h) is True

    def test_verify_returns_false_for_wrong(self, user_service):
        salt = b"0123456789abcdef"
        h = user_service._hash_password("correct", salt)
        assert user_service._verify_password("wrong", salt, h) is False


# ---------------------------------------------------------------------------
# UserService.authenticate
# ---------------------------------------------------------------------------

class TestUserServiceAuthenticate:

    def _make_user_row(self, svc: UserService, username="alice", password="testpassword", expired=False):
        salt = svc._generate_salt()
        pw_hash = svc._hash_password(password, salt)
        uid = uuid.uuid4()
        return {
            "id": uid.bytes,
            "username": username,
            "email": f"{username}@example.com",
            "first_name": "Alice",
            "last_name": "Smith",
            "password_hash": pw_hash,
            "salt": salt,
            "auth_source": "local",
            "must_change_pw": 0,
            "expires_at": 1 if expired else None,
        }

    def test_valid_credentials_succeed(self, user_service, mock_repo):
        row = self._make_user_row(user_service, password="goodpassword")
        mock_repo.get_user_for_login.return_value = row
        result = user_service.authenticate("alice", "goodpassword")
        assert result.success is True

    def test_wrong_password_fails(self, user_service, mock_repo):
        row = self._make_user_row(user_service, password="goodpassword")
        mock_repo.get_user_for_login.return_value = row
        result = user_service.authenticate("alice", "wrongpassword")
        assert result.success is False

    def test_unknown_user_fails(self, user_service, mock_repo):
        mock_repo.get_user_for_login.return_value = None
        result = user_service.authenticate("nobody", "any")
        assert result.success is False

    def test_expired_account_fails(self, user_service, mock_repo):
        row = self._make_user_row(user_service, password="pw", expired=True)
        mock_repo.get_user_for_login.return_value = row
        result = user_service.authenticate("alice", "pw")
        assert result.success is False
        assert "expired" in result.message.lower()

    def test_ldap_user_not_verified_locally(self, user_service, mock_repo):
        salt = user_service._generate_salt()
        uid = uuid.uuid4()
        mock_repo.get_user_for_login.return_value = {
            "id": uid.bytes,
            "username": "ldapuser",
            "email": "ldap@example.com",
            "first_name": "L",
            "last_name": "D",
            "password_hash": b"\x00" * 32,
            "salt": salt,
            "auth_source": "ldap",
            "must_change_pw": 0,
            "expires_at": None,
        }
        result = user_service.authenticate("ldapuser", "any")
        assert result.success is False
        assert result.auth_source == "ldap"


# ---------------------------------------------------------------------------
# AuthenticationService.authenticate (local + LDAP fallthrough)
# ---------------------------------------------------------------------------

class TestAuthServiceAuthenticate:

    def test_local_success_returned_directly(self, auth_service, mock_user_service):
        uid = uuid.uuid4()
        mock_user_service.authenticate.return_value = AuthResult(
            success=True, message="ok", user_id=uid
        )
        result = auth_service.authenticate("alice", "pw")
        assert result.success is True
        assert result.auth_source == "local"

    def test_nack_when_local_fails_and_no_ldap(self, auth_service, mock_user_service):
        mock_user_service.authenticate.return_value = AuthResult(success=False, message="bad")
        result = auth_service.authenticate("alice", "wrong")
        assert result.success is False

    def test_ldap_fallback_when_local_fails(self, mock_user_service):
        new_uid = uuid.uuid4()
        mock_ldap = MagicMock()
        # Local auth: fails with no user_id (unknown user locally)
        mock_user_service.authenticate.return_value = AuthResult(success=False, message="bad")
        # LDAP succeeds
        mock_ldap.authenticate.return_value = AuthResult(
            success=True, message="ldap ok",
            user_id=new_uid, username="alice", email="alice@example.com",
            first_name="Alice", last_name="Smith",
        )
        # create_user called for auto-provisioning — must return a UUID
        mock_user_service.create_user.return_value = new_uid

        svc = AuthenticationService(local=mock_user_service, ldap=mock_ldap)
        result = svc.authenticate("alice", "pw")
        assert result.success is True


# ---------------------------------------------------------------------------
# UserService.create_user
# ---------------------------------------------------------------------------

class TestCreateUser:

    def test_persists_user_and_returns_uuid(self, user_service, mock_repo):
        mock_repo.get_role_by_name.return_value = {"id": 2, "name": "user"}
        uid = user_service.create_user(
            username="newuser",
            email="new@x.com",
            password="validpassword123",
            first_name="New",
            last_name="User",
        )
        assert isinstance(uid, uuid.UUID)
        mock_repo.insert_user.assert_called_once()

    def test_raises_on_short_username(self, user_service):
        from hestia.domain.exceptions import ValidationError
        with pytest.raises(ValidationError, match="short"):
            user_service.create_user(username="ab", email="e@x.com", password="validpass123",
                                     first_name="A", last_name="B")

    def test_raises_on_short_password(self, user_service):
        from hestia.domain.exceptions import ValidationError
        with pytest.raises(ValidationError, match="short"):
            user_service.create_user(username="validname", email="e@x.com", password="short",
                                     first_name="A", last_name="B")

    def test_password_stored_as_hash(self, user_service, mock_repo):
        mock_repo.get_role_by_name.return_value = {"id": 2, "name": "user"}
        user_service.create_user(username="hashtest", email="h@x.com", password="validpassword!",
                                 first_name="H", last_name="T")
        call_kwargs = mock_repo.insert_user.call_args.kwargs
        assert call_kwargs["password_hash"] != b""
        assert call_kwargs["salt"] != b""
        # Hash should not equal the raw password bytes
        assert call_kwargs["password_hash"] != b"validpassword!"

    def test_duplicate_username_propagates_db_error(self, user_service, mock_repo):
        import sqlite3
        mock_repo.get_role_by_name.return_value = {"id": 2}
        mock_repo.insert_user.side_effect = Exception("UNIQUE constraint failed: users.username")
        with pytest.raises(Exception, match="UNIQUE"):
            user_service.create_user(username="dupuser", email="d@x.com", password="validpassword!",
                                     first_name="D", last_name="U")


# ---------------------------------------------------------------------------
# UserService.reset_user_password
# ---------------------------------------------------------------------------

class TestResetUserPassword:

    def test_raises_on_short_password(self, user_service):
        from hestia.domain.exceptions import ValidationError
        with pytest.raises(ValidationError, match="at least"):
            user_service.reset_user_password(uuid.uuid4(), "short")

    def test_updates_hash_and_sets_must_change(self, user_service, mock_repo):
        uid = uuid.uuid4()
        user_service.reset_user_password(uid, "newvalidpassword!")
        mock_repo.update_user_password.assert_called_once()
        mock_repo.set_must_change_pw.assert_called_once()
        call_kwargs = mock_repo.set_must_change_pw.call_args.kwargs
        assert call_kwargs["change"] == 1


# ---------------------------------------------------------------------------
# UserService.change_password
# ---------------------------------------------------------------------------

class TestChangePassword:

    def _user_row(self, svc: UserService, password: str, auth_source="local"):
        salt = svc._generate_salt()
        pw_hash = svc._hash_password(password, salt)
        return {"id": uuid.uuid4().bytes, "auth_source": auth_source,
                "password_hash": pw_hash, "salt": salt}

    def test_succeeds_with_correct_current_password(self, user_service, mock_repo):
        row = self._user_row(user_service, "currentpass!")
        mock_repo.get_user_by_id.return_value = row
        user_service.change_password(uuid.uuid4(), "currentpass!", "newvalidpass!")
        mock_repo.update_user_password.assert_called_once()

    def test_raises_on_wrong_current_password(self, user_service, mock_repo):
        from hestia.domain.exceptions import ValidationError
        row = self._user_row(user_service, "correctpass!")
        mock_repo.get_user_by_id.return_value = row
        with pytest.raises(ValidationError, match="Incorrect"):
            user_service.change_password(uuid.uuid4(), "wrongpass!", "newvalidpass!")

    def test_raises_for_federated_account(self, user_service, mock_repo):
        from hestia.domain.exceptions import ForbiddenError
        row = self._user_row(user_service, "x", auth_source="oidc")
        mock_repo.get_user_by_id.return_value = row
        with pytest.raises(ForbiddenError):
            user_service.change_password(uuid.uuid4(), "any", "newvalidpass!")

    def test_raises_on_short_new_password(self, user_service, mock_repo):
        from hestia.domain.exceptions import ValidationError
        row = self._user_row(user_service, "correct!!")
        mock_repo.get_user_by_id.return_value = row
        with pytest.raises(ValidationError, match="characters"):
            user_service.change_password(uuid.uuid4(), "correct!!", "short")


# ---------------------------------------------------------------------------
# UserService.compute_user_permissions
# ---------------------------------------------------------------------------

class TestComputeUserPermissions:

    def test_admin_role_sets_is_admin(self, user_service, mock_repo):
        uid = uuid.uuid4()
        mock_repo.get_role_by_name.return_value = {"id": 1, "name": "admin"}
        mock_repo.get_user_roles.return_value = [{"id": 1, "name": "admin"}]
        mock_repo.get_user_org_memberships.return_value = []
        perms = user_service.compute_user_permissions(uid)
        assert perms.is_admin is True

    def test_non_admin_role_sets_is_admin_false(self, user_service, mock_repo):
        uid = uuid.uuid4()
        mock_repo.get_role_by_name.return_value = {"id": 1, "name": "admin"}
        mock_repo.get_user_roles.return_value = [{"id": 2, "name": "user"}]
        mock_repo.get_user_org_memberships.return_value = []
        perms = user_service.compute_user_permissions(uid)
        assert perms.is_admin is False

    def test_tenant_moderator_in_moderated_tenants(self, user_service, mock_repo):
        uid = uuid.uuid4()
        mock_repo.get_role_by_name.return_value = {"id": 1}
        mock_repo.get_user_roles.return_value = []
        mock_repo.get_user_org_memberships.return_value = [
            {"org_id": 5, "tenant_role": "moderator", "classification_level": 2}
        ]
        mock_repo.get_tenant_collections.return_value = []
        perms = user_service.compute_user_permissions(uid)
        assert 5 in perms.moderated_tenants

    def test_collection_access_from_tenant_membership(self, user_service, mock_repo):
        uid = uuid.uuid4()
        mock_repo.get_role_by_name.return_value = {"id": 1}
        mock_repo.get_user_roles.return_value = []
        mock_repo.get_user_org_memberships.return_value = [
            {"org_id": 3, "tenant_role": None, "classification_level": 3}
        ]
        mock_repo.get_tenant_collections.return_value = [
            {"collection_id": "col-a", "max_classification": 2}
        ]
        perms = user_service.compute_user_permissions(uid)
        assert "col-a" in perms.allowed_collections
        assert perms.allowed_collections["col-a"].access is True


# ---------------------------------------------------------------------------
# UserService.set_member_tenant_role
# ---------------------------------------------------------------------------

class TestSetMemberTenantRole:

    def test_allows_moderator_when_no_existing(self, user_service, mock_repo):
        uid = uuid.uuid4()
        mock_repo.get_org_tenant_moderator.return_value = None
        user_service.set_member_tenant_role(uid, org_id=1, role="moderator")
        mock_repo.set_member_tenant_role.assert_called_once()

    def test_raises_when_another_moderator_exists(self, user_service, mock_repo):
        from hestia.domain.exceptions import ValidationError
        existing_uid = uuid.uuid4()
        mock_repo.get_org_tenant_moderator.return_value = {"user_id": existing_uid.bytes}
        with pytest.raises(ValidationError, match="moderator"):
            user_service.set_member_tenant_role(uuid.uuid4(), org_id=1, role="moderator")

    def test_allows_same_user_reassigned(self, user_service, mock_repo):
        uid = uuid.uuid4()
        mock_repo.get_org_tenant_moderator.return_value = {"user_id": uid.bytes}
        user_service.set_member_tenant_role(uid, org_id=1, role="moderator")
        mock_repo.set_member_tenant_role.assert_called_once()


# ---------------------------------------------------------------------------
# UserService.assert_conversation_owner
# ---------------------------------------------------------------------------

class TestAssertConversationOwner:

    def test_passes_for_owner(self, user_service, mock_repo):
        uid = uuid.uuid4()
        c_id = uuid.uuid4()
        mock_repo.get_conversation_owner.return_value = {"user_id": uid.bytes}
        user_service.assert_conversation_owner(uid, c_id)  # should not raise

    def test_raises_for_non_owner(self, user_service, mock_repo):
        from hestia.domain.exceptions import NotFoundError
        uid = uuid.uuid4()
        other = uuid.uuid4()
        c_id = uuid.uuid4()
        mock_repo.get_conversation_owner.return_value = {"user_id": other.bytes}
        with pytest.raises(NotFoundError):
            user_service.assert_conversation_owner(uid, c_id)

    def test_raises_when_conversation_not_found(self, user_service, mock_repo):
        from hestia.domain.exceptions import NotFoundError
        mock_repo.get_conversation_owner.return_value = None
        with pytest.raises(NotFoundError):
            user_service.assert_conversation_owner(uuid.uuid4(), uuid.uuid4())


# ---------------------------------------------------------------------------
# UserService.append_conversation_message
# ---------------------------------------------------------------------------

class TestAppendConversationMessage:

    def test_stores_text_content_from_multimodal_list(self, user_service, mock_repo):
        uid = uuid.uuid4()
        c_id = uuid.uuid4()
        mock_repo.get_conversation_owner.return_value = {"user_id": uid.bytes}
        mock_repo.insert_message.return_value = None
        mock_repo.update_conversation_updated_at.return_value = None

        content = [{"type": "text", "text": "Hello"}, {"type": "image_url", "url": "..."}]
        user_service.append_conversation_message(uid, c_id, role="user", content=content)

        call_kwargs = mock_repo.insert_message.call_args.kwargs
        assert call_kwargs["content"] == "Hello"

    def test_stores_plain_string_unchanged(self, user_service, mock_repo):
        uid = uuid.uuid4()
        c_id = uuid.uuid4()
        mock_repo.get_conversation_owner.return_value = {"user_id": uid.bytes}
        user_service.append_conversation_message(uid, c_id, role="user", content="plain text")
        call_kwargs = mock_repo.insert_message.call_args.kwargs
        assert call_kwargs["content"] == "plain text"

    def test_returns_message_uuid(self, user_service, mock_repo):
        uid = uuid.uuid4()
        c_id = uuid.uuid4()
        mock_repo.get_conversation_owner.return_value = {"user_id": uid.bytes}
        result = user_service.append_conversation_message(uid, c_id, role="user", content="hi")
        assert isinstance(result, uuid.UUID)


# ---------------------------------------------------------------------------
# LDAPService._escape_dn_value
# ---------------------------------------------------------------------------

class TestEscapeDnValue:

    @pytest.fixture
    def ldap_svc(self):
        from hestia.domain.auth.users import LDAPService
        return LDAPService(host="ldap.example.com", search_base="dc=example,dc=com")

    def test_escapes_comma(self, ldap_svc):
        result = ldap_svc._escape_dn_value("a,b")
        assert "\\," in result

    def test_escapes_backslash(self, ldap_svc):
        result = ldap_svc._escape_dn_value("a\\b")
        assert "\\\\" in result

    def test_escapes_leading_space(self, ldap_svc):
        result = ldap_svc._escape_dn_value(" leading")
        assert result.startswith("\\")

    def test_escapes_leading_hash(self, ldap_svc):
        result = ldap_svc._escape_dn_value("#hash")
        assert result.startswith("\\")

    def test_plain_value_unchanged(self, ldap_svc):
        assert ldap_svc._escape_dn_value("johndoe") == "johndoe"


# ---------------------------------------------------------------------------
# LDAPService._normalize_ldap_groups
# ---------------------------------------------------------------------------

class TestNormalizeLdapGroups:

    @pytest.fixture
    def ldap_svc(self):
        from hestia.domain.auth.users import LDAPService
        return LDAPService(host="ldap.example.com", search_base="dc=example,dc=com")

    def test_extracts_cn_from_dn(self, ldap_svc):
        groups = ldap_svc._normalize_ldap_groups(
            ["CN=HestiaAdmins,OU=Groups,DC=example,DC=com"]
        )
        assert "hestiaadmins" in groups

    def test_lowercases_group_name(self, ldap_svc):
        groups = ldap_svc._normalize_ldap_groups(["CN=MyGroup,DC=example,DC=com"])
        assert "mygroup" in groups

    def test_ignores_non_cn_dns(self, ldap_svc):
        groups = ldap_svc._normalize_ldap_groups(["OU=Users,DC=example,DC=com"])
        assert len(groups) == 0

    def test_multiple_groups(self, ldap_svc):
        groups = ldap_svc._normalize_ldap_groups([
            "CN=GroupA,DC=example,DC=com",
            "CN=GroupB,DC=example,DC=com",
        ])
        assert groups == {"groupa", "groupb"}


# ---------------------------------------------------------------------------
# LDAPService._search_user
# ---------------------------------------------------------------------------

class TestSearchUser:

    @pytest.fixture
    def ldap_svc(self):
        from hestia.domain.auth.users import LDAPService
        return LDAPService(
            host="ldap.example.com",
            search_base="dc=example,dc=com",
            user_attribute="uid",
            mail_attribute="mail",
        )

    def test_returns_dn_and_attrs_on_success(self, ldap_svc):
        conn = MagicMock()
        entry = MagicMock()
        entry.entry_dn = "uid=alice,dc=example,dc=com"
        entry.entry_attributes_as_dict = {"uid": ["alice"], "mail": ["alice@example.com"]}
        conn.entries = [entry]
        dn, attrs = ldap_svc._search_user(conn, "alice")
        assert dn == "uid=alice,dc=example,dc=com"
        assert attrs is not None

    def test_tries_mail_attribute_as_fallback(self, ldap_svc):
        conn = MagicMock()
        entry = MagicMock()
        entry.entry_dn = "uid=alice,dc=example,dc=com"
        entry.entry_attributes_as_dict = {"uid": ["alice"]}

        # First call (uid filter) returns nothing, second call (mail filter) returns entry
        conn.entries = []

        call_count = [0]
        def side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 2:
                conn.entries = [entry]

        conn.search.side_effect = side_effect
        dn, attrs = ldap_svc._search_user(conn, "alice@example.com")
        assert conn.search.call_count == 2

    def test_returns_none_when_not_found(self, ldap_svc):
        conn = MagicMock()
        conn.entries = []
        dn, attrs = ldap_svc._search_user(conn, "nobody")
        assert dn is None
        assert attrs is None
