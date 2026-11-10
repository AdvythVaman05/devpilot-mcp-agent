"""
Unit Tests for Authentication Service
"""
import pytest
from auth_service.auth import (
    generate_token,
    verify_token,
    hash_password,
    verify_password,
    check_role_permission,
)
from auth_service.models import (
    TokenExpiredError,
    InvalidTokenError,
    PermissionDeniedError,
)

SECRET = "super_secure_enterprise_jwt_secret_998877"


def test_hash_and_verify_password():
    """Verify that password hashing and constant-time verification work correctly."""
    pwd = "CorrectHorseBatteryStaple42!"
    hashed = hash_password(pwd)
    assert hashed != pwd
    assert verify_password(pwd, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False


def test_role_permission_hierarchy():
    """Verify that user role hierarchy is enforced correctly."""
    assert check_role_permission("admin", "developer") is True
    assert check_role_permission("developer", "viewer") is True
    
    with pytest.raises(PermissionDeniedError):
        check_role_permission("viewer", "developer")


def test_token_tampered_signature_rejected():
    """Verify that tokens with modified headers or payloads are rejected."""
    token = generate_token("user_101", SECRET)
    parts = token.split(".")
    tampered_token = f"{parts[0]}.{parts[1]}.invalidsignature"
    
    with pytest.raises(InvalidTokenError):
        verify_token(tampered_token, SECRET)


def test_valid_token_verification():
    """
    CRITICAL TEST: Verify that a freshly issued token verifies successfully.
    A token created with a 3600-second expiration must decode and return
    the user payload without raising TokenExpiredError.
    """
    token = generate_token(user_id="dev_user_77", secret=SECRET, role="developer", expires_in=3600)
    payload = verify_token(token, SECRET)
    
    assert payload["sub"] == "dev_user_77"
    assert payload["role"] == "developer"
    assert "exp" in payload
