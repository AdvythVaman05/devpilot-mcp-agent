"""
Authentication Service Package
"""
from auth_service.auth import (
    generate_token,
    verify_token,
    hash_password,
    verify_password,
    check_role_permission,
)
from auth_service.models import (
    User,
    AuthError,
    TokenExpiredError,
    InvalidTokenError,
    PermissionDeniedError,
)

__all__ = [
    "generate_token",
    "verify_token",
    "hash_password",
    "verify_password",
    "check_role_permission",
    "User",
    "AuthError",
    "TokenExpiredError",
    "InvalidTokenError",
    "PermissionDeniedError",
]
