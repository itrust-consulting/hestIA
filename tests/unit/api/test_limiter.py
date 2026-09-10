from __future__ import annotations

from unittest.mock import MagicMock

from starlette.datastructures import Headers

from hestia.api.limiter import login_ip_key, login_ip_rate_limit, login_key


def _request(headers: dict[str, str] | None = None, client_host: str = "10.0.0.7"):
    request = MagicMock()
    request.headers = Headers(headers or {})
    request.client.host = client_host
    return request


# ---------------------------------------------------------------------------
# login_ip_key / login_ip_rate_limit
# ---------------------------------------------------------------------------

class TestLoginIpKey:

    def test_reads_x_forwarded_for_header(self):
        # A real Starlette Headers object, built from the standard
        # hyphenated "X-Forwarded-For" header a real proxy sends -- unlike
        # a plain dict keyed on the literal "X_FORWARDED_FOR", this
        # exercises Starlette's actual (case-insensitive, hyphen-preserving)
        # header lookup that slowapi's get_ipaddr is incompatible with.
        request = _request({"X-Forwarded-For": "203.0.113.5"})
        assert login_ip_key(request) == "203.0.113.5"

    def test_uses_first_address_in_forwarded_chain(self):
        request = _request({"X-Forwarded-For": "203.0.113.5, 10.0.0.1"})
        assert login_ip_key(request) == "203.0.113.5"

    def test_underscore_variant_does_not_match(self):
        # Regression guard: slowapi's get_ipaddr looks up the literal key
        # "X_FORWARDED_FOR" (underscore), which never matches a real
        # "X-Forwarded-For" header via Starlette's Headers -- confirms the
        # fix no longer depends on that broken lookup.
        request = _request({"X_Forwarded_For": "203.0.113.5"}, client_host="10.0.0.7")
        assert login_ip_key(request) == "10.0.0.7"

    def test_falls_back_to_socket_address(self):
        request = _request({}, client_host="10.0.0.7")
        assert login_ip_key(request) == "10.0.0.7"

    def test_is_independent_of_login_key(self):
        # login_key (per-username) and login_ip_key (per-source-address) key
        # off different request data -- a spraying attacker who varies the
        # username but not the source address must still be caught by the
        # IP-keyed limiter even though each username gets its own fresh
        # login_key budget.
        request = _request({}, client_host="10.0.0.7")
        request.state.login_identifier = "victim-username"
        assert login_key(request) == "victim-username"
        assert login_ip_key(request) == "10.0.0.7"


class TestLoginIpRateLimit:

    def test_default_is_looser_than_per_username_limit(self):
        # Sanity check on the constant itself -- this must stay generous
        # enough that ordinary shared-frontend traffic (see login_ip_key's
        # docstring) doesn't trip it.
        assert login_ip_rate_limit() == "30/minute"

    def test_configure_overrides_default(self):
        login_ip_rate_limit.configure(50, 2)
        try:
            assert login_ip_rate_limit() == "50 per 2 minutes"
        finally:
            login_ip_rate_limit.configure(30, 1)
