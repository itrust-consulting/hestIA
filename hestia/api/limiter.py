from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordRequestForm
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)


async def stash_login_identifier(request: Request, form_data: OAuth2PasswordRequestForm = Depends()) -> None:
    """Dependency-only side effect for the /login route: stash the attempted
    username on request.state so `login_key` (a synchronous slowapi
    key_func) can read it without re-parsing the body. FastAPI resolves all
    of a route's Depends() -- including this one -- before calling the
    (slowapi-wrapped) endpoint, so this always runs before login_key does."""
    request.state.login_identifier = form_data.username


def login_key(request: Request) -> str:
    """Rate-limit key for the /login route -- keyed on the attempted
    username/email rather than source IP. Every browser login is proxied
    through hestia-ui's server-side routes, so an IP-based key collapses
    every real user onto the frontend container's one address: the
    configured lockout would then apply to the whole deployment instead of
    one account. Falls back to source IP only if the identifier wasn't
    stashed (stash_login_identifier not wired in, or a malformed request
    slowapi still needs to key somehow)."""
    identifier = getattr(request.state, "login_identifier", None)
    return identifier or get_remote_address(request)


class _LoginRateLimit:
    def __init__(self, default: str = "5/minute") -> None:
        self._value = default

    def __call__(self) -> str:
        return self._value

    def configure(self, max_attempts: int, window_minutes: int) -> None:
        self._value = f"{max_attempts} per {window_minutes} minutes"


login_rate_limit = _LoginRateLimit()
