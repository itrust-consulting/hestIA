from __future__ import annotations


class HestiaError(Exception):
    status_code: int = 500

    def __init__(self, message: str = "Internal server error"):
        super().__init__(message)
        self.message = message


class AuthError(HestiaError):
    status_code = 401


class ForbiddenError(HestiaError):
    status_code = 403


class NotFoundError(HestiaError):
    status_code = 404


class ValidationError(HestiaError):
    status_code = 400


class ProviderError(HestiaError):
    """Upstream LLM or vector DB failure."""
    status_code = 502


class ConfigurationError(HestiaError):
    """Missing or invalid server-side configuration."""
    status_code = 500
