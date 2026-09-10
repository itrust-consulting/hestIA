from __future__ import annotations

import json
import time
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
    repo = MagicMock()
    # create_user's duplicate-username/email pre-check needs an explicit
    # "nothing found" default -- otherwise a bare MagicMock return value is
    # truthy and every test here would hit the "already taken" branch.
    repo.get_user_by_username.return_value = None
    repo.get_user_by_email.return_value = None
    return repo


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

    def test_future_expires_at_account_succeeds(self, user_service, mock_repo):
        # Regression test: expires_at is epoch SECONDS, but the expiry check
        # used to compare it against now_epoch() (milliseconds) unconverted,
        # so any account with an expires_at -- however far in the future --
        # was treated as already expired.
        row = self._make_user_row(user_service, password="pw")
        row["expires_at"] = int(time.time()) + 3600
        mock_repo.get_user_for_login.return_value = row
        result = user_service.authenticate("alice", "pw")
        assert result.success is True

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

    def test_duplicate_username_raises_clean_validation_error(self, user_service, mock_repo):
        # A double-submit (or a genuinely taken username) is now caught by a
        # pre-check and raised as a clean, user-facing message instead of
        # letting sqlite3.IntegrityError surface as a raw 500.
        from hestia.domain.exceptions import ValidationError
        mock_repo.get_user_by_username.return_value = {"id": uuid.uuid4().bytes}
        with pytest.raises(ValidationError, match="username is already taken"):
            user_service.create_user(username="dupuser", email="d@x.com", password="validpassword!",
                                     first_name="D", last_name="U")
        mock_repo.insert_user.assert_not_called()

    def test_duplicate_email_raises_clean_validation_error(self, user_service, mock_repo):
        from hestia.domain.exceptions import ValidationError
        mock_repo.get_user_by_email.return_value = {"id": uuid.uuid4().bytes}
        with pytest.raises(ValidationError, match="email is already registered"):
            user_service.create_user(username="newuser2", email="dup@x.com", password="validpassword!",
                                     first_name="D", last_name="U")
        mock_repo.insert_user.assert_not_called()

    def test_genuine_race_past_the_precheck_still_propagates(self, user_service, mock_repo):
        # The pre-check narrows the common case (double-click, stale form)
        # but doesn't claim to close every race -- if insert_user itself
        # still hits the UNIQUE constraint, that must still surface rather
        # than being silently swallowed.
        mock_repo.get_role_by_name.return_value = {"id": 2}
        mock_repo.insert_user.side_effect = Exception("UNIQUE constraint failed: users.username")
        with pytest.raises(Exception, match="UNIQUE"):
            user_service.create_user(username="dupuser", email="d@x.com", password="validpassword!",
                                     first_name="D", last_name="U")


# ---------------------------------------------------------------------------
# UserService.create_org
# ---------------------------------------------------------------------------

class TestCreateOrg:

    def test_returns_true_when_created(self, user_service, mock_repo):
        mock_repo.insert_organization.return_value = True
        assert user_service.create_org("Acme", "AC") is True

    def test_returns_false_on_name_or_abbreviation_collision(self, user_service, mock_repo):
        # insert_organization's INSERT OR IGNORE silently no-ops on a
        # collision -- create_org must propagate that instead of masking it.
        mock_repo.insert_organization.return_value = False
        assert user_service.create_org("Acme", "AC") is False


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


# ---------------------------------------------------------------------------
# UserService.compute_user_permissions -- cross-membership collection merge
# ---------------------------------------------------------------------------

class TestComputeUserPermissionsMerge:

    def test_collection_from_two_memberships_keeps_higher_classification(self, user_service, mock_repo):
        uid = uuid.uuid4()
        mock_repo.get_role_by_name.return_value = {"id": 1, "name": "admin"}
        mock_repo.get_user_roles.return_value = []
        mock_repo.get_user_org_memberships.return_value = [
            {"org_id": 1, "tenant_role": None, "classification_level": 1},
            {"org_id": 2, "tenant_role": None, "classification_level": 3},
        ]
        mock_repo.get_tenant_collections.side_effect = lambda org_id: [
            {"collection_id": "col-a", "max_classification": None}
        ]
        perms = user_service.compute_user_permissions(uid)
        assert perms.allowed_collections["col-a"].max_classification == 3

    def test_role_assignable_tenants_only_from_moderator_role(self, user_service, mock_repo):
        uid = uuid.uuid4()
        mock_repo.get_role_by_name.return_value = {"id": 1, "name": "admin"}
        mock_repo.get_user_roles.return_value = []
        mock_repo.get_user_org_memberships.return_value = [
            {"org_id": 1, "tenant_role": "moderator", "classification_level": 1},
            {"org_id": 2, "tenant_role": "co-moderator", "classification_level": 1},
        ]
        mock_repo.get_tenant_collections.return_value = []
        perms = user_service.compute_user_permissions(uid)
        assert perms.role_assignable_tenants == [1]
        assert set(perms.moderated_tenants) == {1, 2}


# ---------------------------------------------------------------------------
# UserService.load_user_profile
# ---------------------------------------------------------------------------

class TestLoadUserProfile:

    def test_returns_none_when_user_missing(self, user_service, mock_repo):
        mock_repo.get_user_by_id.return_value = None
        assert user_service.load_user_profile(uuid.uuid4()) is None

    def test_returns_populated_user_model(self, user_service, mock_repo):
        uid = uuid.uuid4()
        mock_repo.get_user_by_id.return_value = {
            "id": uid.bytes, "username": "bob", "email": "b@x.com",
            "first_name": "Bob", "last_name": "B", "must_change_pw": 0,
            "auth_source": "local", "created_at": 100, "updated_at": 200, "expires_at": None,
        }
        mock_repo.get_role_by_name.return_value = None
        mock_repo.get_user_roles.return_value = []
        mock_repo.get_user_org_memberships.return_value = []
        mock_repo.get_user_organizations.return_value = []
        profile = user_service.load_user_profile(uid)
        assert profile.username == "bob"
        assert profile.id == uid
        assert profile.must_change_pw is False


# ---------------------------------------------------------------------------
# UserService.update_user / delete_user / set_user_expiration
# ---------------------------------------------------------------------------

class TestUpdateUser:

    def test_updates_profile_fields(self, user_service, mock_repo):
        uid = uuid.uuid4()
        mock_repo.get_user_roles.return_value = []
        user_service.update_user(
            uid, username="bob2", email="b2@x.com", first_name="Bob", last_name="B", expires_at=None
        )
        mock_repo.update_user_profile.assert_called_once()
        call_kwargs = mock_repo.update_user_profile.call_args.kwargs
        assert call_kwargs["username"] == "bob2"
        assert call_kwargs["id"] == uid

    def test_role_ids_none_skips_role_sync(self, user_service, mock_repo):
        uid = uuid.uuid4()
        user_service.update_user(
            uid, username="bob", email="b@x.com", first_name="B", last_name="B",
            expires_at=None, role_ids=None,
        )
        mock_repo.add_role_to_user.assert_not_called()
        mock_repo.remove_role_from_user.assert_not_called()
        mock_repo.get_user_roles.assert_not_called()

    def test_role_ids_added_and_removed(self, user_service, mock_repo):
        uid = uuid.uuid4()
        mock_repo.get_user_roles.return_value = [{"id": 1, "name": "user"}, {"id": 2, "name": "moderator"}]
        user_service.update_user(
            uid, username="bob", email="b@x.com", first_name="B", last_name="B",
            expires_at=None, role_ids=[2, 3],
        )
        mock_repo.remove_role_from_user.assert_called_once_with(user_id=uid, role_id=1)
        mock_repo.add_role_to_user.assert_called_once()
        add_kwargs = mock_repo.add_role_to_user.call_args.kwargs
        assert add_kwargs["role_id"] == 3

    def test_role_ids_identical_to_current_makes_no_changes(self, user_service, mock_repo):
        uid = uuid.uuid4()
        mock_repo.get_user_roles.return_value = [{"id": 1, "name": "user"}]
        user_service.update_user(
            uid, username="bob", email="b@x.com", first_name="B", last_name="B",
            expires_at=None, role_ids=[1],
        )
        mock_repo.add_role_to_user.assert_not_called()
        mock_repo.remove_role_from_user.assert_not_called()

    def test_new_password_triggers_reset(self, user_service, mock_repo):
        uid = uuid.uuid4()
        mock_repo.get_user_roles.return_value = []
        user_service.update_user(
            uid, username="bob", email="b@x.com", first_name="B", last_name="B",
            expires_at=None, new_password="newvalidpassword!",
        )
        mock_repo.update_user_password.assert_called_once()
        mock_repo.set_must_change_pw.assert_called_once()

    def test_no_password_does_not_touch_password(self, user_service, mock_repo):
        uid = uuid.uuid4()
        mock_repo.get_user_roles.return_value = []
        user_service.update_user(
            uid, username="bob", email="b@x.com", first_name="B", last_name="B", expires_at=None,
        )
        mock_repo.update_user_password.assert_not_called()

    def test_short_new_password_raises(self, user_service, mock_repo):
        from hestia.domain.exceptions import ValidationError
        uid = uuid.uuid4()
        mock_repo.get_user_roles.return_value = []
        with pytest.raises(ValidationError, match="at least"):
            user_service.update_user(
                uid, username="bob", email="b@x.com", first_name="B", last_name="B",
                expires_at=None, new_password="short",
            )


class TestDeleteUser:

    def test_calls_repo_delete(self, user_service, mock_repo):
        uid = uuid.uuid4()
        user_service.delete_user(uid)
        mock_repo.delete_user.assert_called_once_with(id=uid)


class TestSetUserExpiration:

    def test_calls_repo_set_expiration(self, user_service, mock_repo):
        uid = uuid.uuid4()
        user_service.set_user_expiration(uid, 12345)
        call_kwargs = mock_repo.set_user_expiration.call_args.kwargs
        assert call_kwargs["id"] == uid
        assert call_kwargs["expires_ts"] == 12345


# ---------------------------------------------------------------------------
# UserService.get_tenant_collection_info / get_tenant_summary
# ---------------------------------------------------------------------------

class TestGetTenantCollectionInfo:

    def test_splits_owned_and_accessible(self, user_service, mock_repo):
        mock_repo.get_tenant_collections.return_value = [
            {"collection_id": "col-owned", "role": "owner", "max_classification": None},
            {"collection_id": "col-access", "role": "access", "max_classification": 2},
        ]
        mock_repo.get_collection_access_tenants.return_value = [
            {"id": 2, "name": "OrgB", "abbreviation": "OB", "max_classification": 3},
        ]
        mock_repo.get_collection_owner.return_value = {"id": 3, "name": "OrgC", "abbreviation": "OC"}
        result = user_service.get_tenant_collection_info(1)
        assert len(result["owned"]) == 1
        assert result["owned"][0]["id"] == "col-owned"
        assert result["owned"][0]["access"][0]["name"] == "OrgB"
        assert len(result["accessible"]) == 1
        assert result["accessible"][0]["owner"]["name"] == "OrgC"

    def test_accessible_collection_with_no_owner(self, user_service, mock_repo):
        mock_repo.get_tenant_collections.return_value = [
            {"collection_id": "col-x", "role": "access", "max_classification": None},
        ]
        mock_repo.get_collection_owner.return_value = None
        result = user_service.get_tenant_collection_info(1)
        assert result["accessible"][0]["owner"] is None

    def test_no_collections_returns_empty_lists(self, user_service, mock_repo):
        mock_repo.get_tenant_collections.return_value = []
        result = user_service.get_tenant_collection_info(1)
        assert result == {"owned": [], "accessible": []}


class TestGetTenantSummary:

    def test_returns_counts_and_own_membership_level(self, user_service, mock_repo):
        uid = uuid.uuid4()
        mock_repo.get_tenant_collections.return_value = [
            {"collection_id": "col-owned", "role": "owner", "max_classification": None},
            {"collection_id": "col-access", "role": "access", "max_classification": None},
        ]
        mock_repo.get_collection_access_tenants.return_value = []
        mock_repo.get_organization_users.return_value = [1, 2, 3]
        mock_repo.get_user_org_memberships.return_value = [{"org_id": 1, "classification_level": 2}]
        result = user_service.get_tenant_summary(1, uid)
        assert result["member_count"] == 3
        assert result["owned_collections"] == ["col-owned"]
        assert result["accessible_collections"] == ["col-access"]
        assert result["classification_level"] == 2

    def test_classification_level_none_when_not_a_member(self, user_service, mock_repo):
        mock_repo.get_tenant_collections.return_value = []
        mock_repo.get_organization_users.return_value = []
        mock_repo.get_user_org_memberships.return_value = []
        result = user_service.get_tenant_summary(1, uuid.uuid4())
        assert result["classification_level"] is None

    def test_does_not_expose_member_identities(self, user_service, mock_repo):
        # Self-service summary must only ever surface a headcount, never the
        # underlying member rows (which carry usernames/names).
        mock_repo.get_tenant_collections.return_value = []
        mock_repo.get_organization_users.return_value = [
            {"username": "shouldnotleak"}, {"username": "alsoshouldnotleak"},
        ]
        mock_repo.get_user_org_memberships.return_value = []
        result = user_service.get_tenant_summary(1, uuid.uuid4())
        assert result == {
            "member_count": 2, "owned_collections": [], "accessible_collections": [],
            "classification_level": None,
        }


# ---------------------------------------------------------------------------
# UserService collection-grant management
# ---------------------------------------------------------------------------

class TestCollectionGrants:

    def test_get_collection_grants_with_owner(self, user_service, mock_repo):
        mock_repo.get_collection_owner.return_value = {"id": 1, "name": "OrgA", "abbreviation": "OA"}
        mock_repo.get_collection_access_tenants.return_value = [
            {"id": 2, "name": "OrgB", "abbreviation": "OB", "max_classification": 1},
        ]
        result = user_service.get_collection_grants("col-1")
        assert result["owner"]["name"] == "OrgA"
        assert result["access"][0]["name"] == "OrgB"

    def test_get_collection_grants_no_owner(self, user_service, mock_repo):
        mock_repo.get_collection_owner.return_value = None
        mock_repo.get_collection_access_tenants.return_value = []
        result = user_service.get_collection_grants("col-1")
        assert result["owner"] is None
        assert result["access"] == []

    def test_add_tenant_collection_passes_through(self, user_service, mock_repo):
        user_service.add_tenant_collection(1, "col-1", role="owner", max_classification=3)
        mock_repo.add_tenant_collection.assert_called_once_with(
            org_id=1, collection_id="col-1", role="owner", max_classification=3
        )

    def test_add_tenant_collection_defaults(self, user_service, mock_repo):
        user_service.add_tenant_collection(1, "col-1")
        mock_repo.add_tenant_collection.assert_called_once_with(
            org_id=1, collection_id="col-1", role="access", max_classification=None
        )

    def test_remove_tenant_collection_passes_through(self, user_service, mock_repo):
        user_service.remove_tenant_collection(1, "col-1")
        mock_repo.remove_tenant_collection.assert_called_once_with(org_id=1, collection_id="col-1")

    def test_remove_collection_grants_passes_through(self, user_service, mock_repo):
        user_service.remove_collection_grants("col-1")
        mock_repo.remove_collection_grants.assert_called_once_with(collection_id="col-1")


# ---------------------------------------------------------------------------
# UserService self-service: change_username / change_email / deactivate
# ---------------------------------------------------------------------------

class TestChangePasswordExtra:

    def test_raises_when_user_not_found(self, user_service, mock_repo):
        from hestia.domain.exceptions import NotFoundError
        mock_repo.get_user_by_id.return_value = None
        with pytest.raises(NotFoundError):
            user_service.change_password(uuid.uuid4(), "a", "newvalidpass!")

    def test_raises_for_ldap_federated_account(self, user_service, mock_repo):
        from hestia.domain.exceptions import ForbiddenError
        mock_repo.get_user_by_id.return_value = {
            "id": uuid.uuid4().bytes, "auth_source": "ldap",
            "password_hash": b"\x00" * 32, "salt": b"\x00" * 16,
        }
        with pytest.raises(ForbiddenError):
            user_service.change_password(uuid.uuid4(), "any", "newvalidpass!")


class TestChangeUsername:

    def test_updates_username(self, user_service, mock_repo):
        uid = uuid.uuid4()
        user_service.change_username(uid, "newname")
        mock_repo.update_username.assert_called_once()
        call_kwargs = mock_repo.update_username.call_args.kwargs
        assert call_kwargs["id"] == uid
        assert call_kwargs["new_username"] == "newname"

    def test_raises_on_short_username(self, user_service, mock_repo):
        from hestia.domain.exceptions import ValidationError
        with pytest.raises(ValidationError, match="short"):
            user_service.change_username(uuid.uuid4(), "ab")
        mock_repo.update_username.assert_not_called()


class TestChangeEmail:

    def test_updates_email(self, user_service, mock_repo):
        uid = uuid.uuid4()
        user_service.change_email(uid, "new@x.com")
        mock_repo.update_user_email.assert_called_once()
        call_kwargs = mock_repo.update_user_email.call_args.kwargs
        assert call_kwargs["id"] == uid
        assert call_kwargs["new_email"] == "new@x.com"

    def test_raises_on_invalid_email(self, user_service, mock_repo):
        from hestia.domain.exceptions import ValidationError
        with pytest.raises(ValidationError, match="Invalid"):
            user_service.change_email(uuid.uuid4(), "not-an-email")
        mock_repo.update_user_email.assert_not_called()


class TestDeactivateUserAccount:

    def test_sets_expiration_to_now(self, user_service, mock_repo):
        uid = uuid.uuid4()
        user_service.deactivate_user_account(uid)
        mock_repo.set_user_expiration.assert_called_once()
        call_kwargs = mock_repo.set_user_expiration.call_args.kwargs
        assert call_kwargs["id"] == uid
        assert call_kwargs["expires_ts"] is not None


# ---------------------------------------------------------------------------
# UserService.get_conversation_messages -- pagination
# ---------------------------------------------------------------------------

class TestGetConversationMessages:

    def test_raises_when_not_owner(self, user_service, mock_repo):
        from hestia.domain.exceptions import NotFoundError
        mock_repo.get_conversation_owner.return_value = None
        with pytest.raises(NotFoundError):
            user_service.get_conversation_messages(uuid.uuid4(), uuid.uuid4())

    def test_requests_limit_plus_one_and_forwards_cursor(self, user_service, mock_repo):
        uid = uuid.uuid4()
        c_id = uuid.uuid4()
        mock_repo.get_conversation_owner.return_value = {"user_id": uid.bytes}
        mock_repo.get_messages.return_value = []
        user_service.get_conversation_messages(uid, c_id, limit=5, before_created_at=10, before_rowid=2)
        call_kwargs = mock_repo.get_messages.call_args.kwargs
        assert call_kwargs["limit"] == 6
        assert call_kwargs["before_created_at"] == 10
        assert call_kwargs["before_rowid"] == 2

    def test_no_extra_row_means_no_more_pages(self, user_service, mock_repo):
        uid = uuid.uuid4()
        c_id = uuid.uuid4()
        mock_repo.get_conversation_owner.return_value = {"user_id": uid.bytes}
        mock_repo.get_messages.return_value = [
            {"id": uuid.uuid4().bytes, "role": "user", "metadata": "{}", "content": "hi",
             "options": "{}", "created_at": 100, "rowid": 1},
        ]
        result = user_service.get_conversation_messages(uid, c_id, limit=20)
        assert result["has_more"] is False
        assert result["next_cursor"] is None
        assert len(result["messages"]) == 1
        assert result["messages"][0]["content"] == "hi"

    def test_extra_row_sets_has_more_and_next_cursor(self, user_service, mock_repo):
        uid = uuid.uuid4()
        c_id = uuid.uuid4()
        mock_repo.get_conversation_owner.return_value = {"user_id": uid.bytes}
        # Repo returns newest-first; service requested limit(2)+1=3 rows.
        rows = [
            {"id": uuid.uuid4().bytes, "role": "user", "metadata": "{}", "content": "newest",
             "options": "{}", "created_at": 300, "rowid": 3},
            {"id": uuid.uuid4().bytes, "role": "user", "metadata": "{}", "content": "middle",
             "options": "{}", "created_at": 200, "rowid": 2},
            {"id": uuid.uuid4().bytes, "role": "user", "metadata": "{}", "content": "oldest-extra",
             "options": "{}", "created_at": 100, "rowid": 1},
        ]
        mock_repo.get_messages.return_value = rows
        result = user_service.get_conversation_messages(uid, c_id, limit=2)
        assert result["has_more"] is True
        assert len(result["messages"]) == 2
        # trimmed to the 2 newest, then re-ordered ascending (oldest of the page first)
        assert [m["content"] for m in result["messages"]] == ["middle", "newest"]
        assert result["next_cursor"] == {"created_at": 200, "rowid": 2}


class TestGetMessagesAfterBoundary:

    def test_raises_when_not_owner(self, user_service, mock_repo):
        from hestia.domain.exceptions import NotFoundError
        mock_repo.get_conversation_owner.return_value = None
        with pytest.raises(NotFoundError):
            user_service.get_messages_after_boundary(uuid.uuid4(), uuid.uuid4(), None, None)

    def test_returns_mapped_messages_and_forwards_boundary(self, user_service, mock_repo):
        uid = uuid.uuid4()
        c_id = uuid.uuid4()
        mock_repo.get_conversation_owner.return_value = {"user_id": uid.bytes}
        mock_repo.get_messages_after.return_value = [
            {"role": "user", "content": "hi", "created_at": 10, "rowid": 1},
            {"role": "assistant", "content": "hello", "created_at": 20, "rowid": 2},
        ]
        result = user_service.get_messages_after_boundary(uid, c_id, boundary_created_at=5, boundary_rowid=0)
        assert len(result) == 2
        assert result[0] == {"role": "user", "content": "hi", "created_at": 10, "rowid": 1}
        call_kwargs = mock_repo.get_messages_after.call_args.kwargs
        assert call_kwargs["after_created_at"] == 5
        assert call_kwargs["after_rowid"] == 0


# ---------------------------------------------------------------------------
# UserService conversation mutation: rename / delete conversation / delete message
# ---------------------------------------------------------------------------

class TestConversationMutation:

    def test_rename_updates_title(self, user_service, mock_repo):
        uid = uuid.uuid4()
        c_id = uuid.uuid4()
        mock_repo.get_conversation_owner.return_value = {"user_id": uid.bytes}
        user_service.rename_user_conversation(uid, c_id, "New Title")
        mock_repo.update_conversation_title.assert_called_once_with(user_id=uid, c_id=c_id, title="New Title")

    def test_rename_raises_when_not_owner(self, user_service, mock_repo):
        from hestia.domain.exceptions import NotFoundError
        mock_repo.get_conversation_owner.return_value = None
        with pytest.raises(NotFoundError):
            user_service.rename_user_conversation(uuid.uuid4(), uuid.uuid4(), "x")

    def test_delete_conversation_calls_repo(self, user_service, mock_repo):
        uid = uuid.uuid4()
        c_id = uuid.uuid4()
        mock_repo.get_conversation_owner.return_value = {"user_id": uid.bytes}
        user_service.delete_user_conversation(uid, c_id)
        mock_repo.delete_conversation.assert_called_once_with(user_id=uid, c_id=c_id)

    def test_delete_conversation_raises_when_not_owner(self, user_service, mock_repo):
        from hestia.domain.exceptions import NotFoundError
        mock_repo.get_conversation_owner.return_value = None
        with pytest.raises(NotFoundError):
            user_service.delete_user_conversation(uuid.uuid4(), uuid.uuid4())

    def test_delete_message_calls_repo(self, user_service, mock_repo):
        uid = uuid.uuid4()
        c_id = uuid.uuid4()
        msg_id = uuid.uuid4()
        mock_repo.get_conversation_owner.return_value = {"user_id": uid.bytes}
        user_service.delete_conversation_message(uid, c_id, msg_id)
        mock_repo.delete_message.assert_called_once_with(c_id=c_id, msg_id=msg_id)

    def test_delete_message_raises_when_not_owner(self, user_service, mock_repo):
        from hestia.domain.exceptions import NotFoundError
        mock_repo.get_conversation_owner.return_value = None
        with pytest.raises(NotFoundError):
            user_service.delete_conversation_message(uuid.uuid4(), uuid.uuid4(), uuid.uuid4())


# ---------------------------------------------------------------------------
# UserService.get_conversation_context_state / update_conversation_context_summary
# ---------------------------------------------------------------------------

class TestConversationContextState:

    def test_returns_empty_dict_when_no_row(self, user_service, mock_repo):
        mock_repo.get_conversation_metadata.return_value = None
        assert user_service.get_conversation_context_state(uuid.uuid4()) == {}

    def test_returns_empty_dict_when_metadata_blank(self, user_service, mock_repo):
        mock_repo.get_conversation_metadata.return_value = {"metadata_json": ""}
        assert user_service.get_conversation_context_state(uuid.uuid4()) == {}

    def test_returns_empty_dict_on_invalid_json(self, user_service, mock_repo):
        mock_repo.get_conversation_metadata.return_value = {"metadata_json": "{not json"}
        assert user_service.get_conversation_context_state(uuid.uuid4()) == {}

    def test_returns_empty_dict_when_json_not_a_dict(self, user_service, mock_repo):
        mock_repo.get_conversation_metadata.return_value = {"metadata_json": "[1, 2, 3]"}
        assert user_service.get_conversation_context_state(uuid.uuid4()) == {}

    def test_parses_valid_dict_json(self, user_service, mock_repo):
        mock_repo.get_conversation_metadata.return_value = {"metadata_json": '{"context_summary": {"summary": "s"}}'}
        result = user_service.get_conversation_context_state(uuid.uuid4())
        assert result == {"context_summary": {"summary": "s"}}

    def test_update_context_summary_persists_merged_metadata(self, user_service, mock_repo):
        c_id = uuid.uuid4()
        mock_repo.get_conversation_metadata.return_value = {"metadata_json": '{"other": 1}'}
        user_service.update_conversation_context_summary(
            c_id, summary="the summary", boundary_created_at=100, boundary_rowid=5
        )
        mock_repo.update_conversation_metadata.assert_called_once()
        call_kwargs = mock_repo.update_conversation_metadata.call_args.kwargs
        assert call_kwargs["c_id"] == c_id
        persisted = json.loads(call_kwargs["metadata_json"])
        assert persisted["other"] == 1
        assert persisted["context_summary"]["summary"] == "the summary"
        assert persisted["context_summary"]["boundary_created_at"] == 100
        assert persisted["context_summary"]["boundary_rowid"] == 5


# ---------------------------------------------------------------------------
# LDAPService._lookup_user_dn -- service-bind-then-fallback-to-direct-bind
# ---------------------------------------------------------------------------

class TestLdapLookupUserDn:

    def test_no_bind_credentials_uses_direct_dn(self):
        from hestia.domain.auth.users import LDAPService
        svc = LDAPService(host="ldap.example.com", search_base="dc=example,dc=com")
        dn, attrs = svc._lookup_user_dn("alice")
        assert dn == "uid=alice,dc=example,dc=com"
        assert attrs is None

    @patch("hestia.domain.auth.users.Connection")
    def test_service_bind_search_finds_user(self, mock_connection_cls):
        from hestia.domain.auth.users import LDAPService
        svc = LDAPService(
            host="ldap.example.com", search_base="dc=example,dc=com",
            bind_dn="cn=svc,dc=example,dc=com", bind_password="pw",
        )
        mock_conn = MagicMock()
        entry = MagicMock()
        entry.entry_dn = "uid=alice,dc=example,dc=com"
        entry.entry_attributes_as_dict = {"uid": ["alice"]}
        mock_conn.entries = [entry]
        mock_connection_cls.return_value = mock_conn
        dn, attrs = svc._lookup_user_dn("alice")
        assert dn == "uid=alice,dc=example,dc=com"
        assert attrs == {"uid": ["alice"]}

    @patch("hestia.domain.auth.users.Connection")
    def test_service_bind_connects_but_no_match_falls_back_to_direct(self, mock_connection_cls):
        from hestia.domain.auth.users import LDAPService
        svc = LDAPService(
            host="ldap.example.com", search_base="dc=example,dc=com",
            bind_dn="cn=svc,dc=example,dc=com", bind_password="pw",
        )
        mock_conn = MagicMock()
        mock_conn.entries = []
        mock_connection_cls.return_value = mock_conn
        dn, attrs = svc._lookup_user_dn("nobody")
        assert dn == "uid=nobody,dc=example,dc=com"
        assert attrs is None

    @patch("hestia.domain.auth.users.Connection")
    def test_service_bind_raises_falls_back_to_direct(self, mock_connection_cls):
        from hestia.domain.auth.users import LDAPService
        svc = LDAPService(
            host="ldap.example.com", search_base="dc=example,dc=com",
            bind_dn="cn=svc,dc=example,dc=com", bind_password="pw",
        )
        mock_connection_cls.side_effect = Exception("bind failed")
        dn, attrs = svc._lookup_user_dn("alice")
        assert dn == "uid=alice,dc=example,dc=com"
        assert attrs is None

    @patch("hestia.domain.auth.users.Connection")
    def test_service_bind_failure_is_logged(self, mock_connection_cls, caplog):
        # Regression test: a service-bind/search failure (directory down,
        # bad bind creds) used to be swallowed with no log at all, showing
        # up only as a generic "login failed" with no cause recorded.
        from hestia.domain.auth.users import LDAPService
        svc = LDAPService(
            host="ldap.example.com", search_base="dc=example,dc=com",
            bind_dn="cn=svc,dc=example,dc=com", bind_password="pw",
        )
        mock_connection_cls.side_effect = Exception("bind failed")
        with caplog.at_level("WARNING", logger="hestia.system"):
            svc._lookup_user_dn("alice")
        assert any(r.message == "ldap_service_bind_failed" for r in caplog.records)

    def test_direct_dn_uses_template_when_configured(self):
        from hestia.domain.auth.users import LDAPService
        svc = LDAPService(
            host="ldap.example.com", search_base="dc=example,dc=com",
            user_dn_template="uid={username},ou=people,dc=example,dc=com",
        )
        dn, attrs = svc._lookup_user_dn("alice")
        assert dn == "uid=alice,ou=people,dc=example,dc=com"
        assert attrs is None


# ---------------------------------------------------------------------------
# LDAPService.authenticate -- bind result + attrs-still-None fallback search
# ---------------------------------------------------------------------------

class TestLdapAuthenticate:

    @pytest.fixture
    def ldap_svc(self):
        from hestia.domain.auth.users import LDAPService
        return LDAPService(host="ldap.example.com", search_base="dc=example,dc=com")

    @patch("hestia.domain.auth.users.Connection")
    def test_bind_failure_returns_nack(self, mock_connection_cls, ldap_svc):
        mock_connection_cls.side_effect = Exception("invalid credentials")
        result = ldap_svc.authenticate("alice", "wrongpw")
        assert result.success is False

    @patch("hestia.domain.auth.users.Connection")
    def test_attrs_none_after_bind_runs_fallback_search(self, mock_connection_cls, ldap_svc):
        bind_conn = MagicMock()
        fallback_conn = MagicMock()
        entry = MagicMock()
        entry.entry_attributes_as_dict = {
            "uid": ["alice"], "mail": ["alice@x.com"], "givenName": ["Alice"], "sn": ["A"], "memberOf": [],
        }
        fallback_conn.entries = [entry]
        mock_connection_cls.side_effect = [bind_conn, fallback_conn]
        result = ldap_svc.authenticate("alice", "pw")
        assert result.success is True
        assert result.username == "alice"
        assert result.email == "alice@x.com"
        assert result.first_name == "Alice"
        assert result.last_name == "A"

    @patch("hestia.domain.auth.users.Connection")
    def test_attrs_none_and_fallback_search_raises_still_succeeds(self, mock_connection_cls, ldap_svc):
        bind_conn = MagicMock()
        mock_connection_cls.side_effect = [bind_conn, Exception("search conn failed")]
        result = ldap_svc.authenticate("alice", "pw")
        assert result.success is True
        assert result.username is None
        assert result.groups == []

    @patch("hestia.domain.auth.users.Connection")
    def test_attrs_none_and_fallback_search_finds_nothing(self, mock_connection_cls, ldap_svc):
        bind_conn = MagicMock()
        fallback_conn = MagicMock()
        fallback_conn.entries = []
        mock_connection_cls.side_effect = [bind_conn, fallback_conn]
        result = ldap_svc.authenticate("alice", "pw")
        assert result.success is True
        assert result.username is None

    @patch("hestia.domain.auth.users.Connection")
    def test_allowed_groups_filters_result(self, mock_connection_cls):
        from hestia.domain.auth.users import LDAPService
        svc = LDAPService(
            host="ldap.example.com", search_base="dc=example,dc=com",
            bind_dn="cn=svc,dc=example,dc=com", bind_password="svcpw",
            allowed_groups={"admins"},
        )
        search_conn = MagicMock()
        entry = MagicMock()
        entry.entry_dn = "uid=alice,dc=example,dc=com"
        entry.entry_attributes_as_dict = {
            "uid": ["alice"],
            "memberOf": ["CN=Admins,DC=x", "CN=Other,DC=x"],
        }
        search_conn.entries = [entry]
        bind_conn = MagicMock()
        mock_connection_cls.side_effect = [search_conn, bind_conn]
        result = svc.authenticate("alice", "pw")
        assert result.success is True
        assert result.groups == ["admins"]

    @patch("hestia.domain.auth.users.Connection")
    def test_no_allowed_groups_configured_keeps_all_groups(self, mock_connection_cls):
        from hestia.domain.auth.users import LDAPService
        svc = LDAPService(host="ldap.example.com", search_base="dc=example,dc=com")
        bind_conn = MagicMock()
        fallback_conn = MagicMock()
        entry = MagicMock()
        entry.entry_attributes_as_dict = {"memberOf": ["CN=GroupA,DC=x", "CN=GroupB,DC=x"]}
        fallback_conn.entries = [entry]
        mock_connection_cls.side_effect = [bind_conn, fallback_conn]
        result = svc.authenticate("alice", "pw")
        assert set(result.groups) == {"groupa", "groupb"}
