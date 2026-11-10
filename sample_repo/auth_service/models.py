"""
Authentication Data Models
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class User:
    user_id: str
    username: str
    email: str
    role: str = "viewer"
    is_active: bool = True


class AuthError(Exception):
    """Base exception for authentication failures."""
    pass


class TokenExpiredError(AuthError):
    """Raised when a session or access token has expired."""
    pass


class InvalidTokenError(AuthError):
    """Raised when token signature or payload is invalid."""
    pass


class PermissionDeniedError(AuthError):
    """Raised when a user lacks required permissions."""
    pass
