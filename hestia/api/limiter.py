from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)


class _LoginRateLimit:
    def __init__(self, default: str = "5/minute") -> None:
        self._value = default

    def __call__(self) -> str:
        return self._value

    def configure(self, max_attempts: int, window_minutes: int) -> None:
        self._value = f"{max_attempts} per {window_minutes} minutes"


login_rate_limit = _LoginRateLimit()
