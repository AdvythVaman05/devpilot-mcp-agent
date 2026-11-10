"""
Authentication & Token Verification Module
"""
import base64
import hashlib
import hmac
import json
import time
from typing import Dict, Any, Optional

from auth_service.models import (
    TokenExpiredError,
    InvalidTokenError,
    PermissionDeniedError,
)


def hash_password(password: str, salt: Optional[str] = None) -> str:
    """Hash a password using SHA-256 with a salt."""
    if not salt:
        salt = "devpilot_static_salt"
    key = hashlib.sha256(f"{salt}:{password}".encode("utf-8")).hexdigest()
    return f"{salt}${key}"


def verify_password(password: str, hashed: str) -> bool:
    """Verify a plain password against the stored salt$hash string."""
    try:
        salt, _ = hashed.split("$", 1)
        expected = hash_password(password, salt=salt)
        return hmac.compare_digest(expected, hashed)
    except Exception:
        return False


def generate_token(user_id: str, secret: str, role: str = "developer", expires_in: int = 3600) -> str:
    """Generate a lightweight HMAC-signed JSON Web Token."""
    now = int(time.time())
    payload = {
        "sub": user_id,
        "role": role,
        "iat": now,
        "exp": now + expires_in,
    }
    header = {"alg": "HS256", "typ": "JWT"}
    
    header_b64 = base64.urlsafe_b64encode(json.dumps(header).encode("utf-8")).decode("utf-8").rstrip("=")
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode("utf-8")).decode("utf-8").rstrip("=")
    
    signing_input = f"{header_b64}.{payload_b64}"
    signature = hmac.new(secret.encode("utf-8"), signing_input.encode("utf-8"), hashlib.sha256).digest()
    sig_b64 = base64.urlsafe_b64encode(signature).decode("utf-8").rstrip("=")
    
    return f"{header_b64}.{payload_b64}.{sig_b64}"


def verify_token(token: str, secret: str) -> Dict[str, Any]:
    """
    Verify signature and expiration of a signed token.
    Returns the decoded payload dict if valid.
    """
    parts = token.split(".")
    if len(parts) != 3:
        raise InvalidTokenError("Malformed token structure: must have 3 parts")
        
    header_b64, payload_b64, sig_b64 = parts
    signing_input = f"{header_b64}.{payload_b64}"
    
    expected_sig = hmac.new(secret.encode("utf-8"), signing_input.encode("utf-8"), hashlib.sha256).digest()
    expected_sig_b64 = base64.urlsafe_b64encode(expected_sig).decode("utf-8").rstrip("=")
    
    if not hmac.compare_digest(sig_b64, expected_sig_b64):
        raise InvalidTokenError("Signature verification failed")
        
    try:
        # Restore base64 padding
        padding = "=" * (4 - len(payload_b64) % 4) if len(payload_b64) % 4 != 0 else ""
        payload_bytes = base64.urlsafe_b64decode(payload_b64 + padding)
        payload = json.loads(payload_bytes.decode("utf-8"))
    except Exception as e:
        raise InvalidTokenError(f"Failed to decode token payload: {str(e)}")
        
    current_time = int(time.time())
    
    # INTENTIONAL BUG: The comparison operator is inverted!
    # A valid token has payload["exp"] in the future (i.e. exp > current_time).
    # Because of the bug below ('>' instead of '<'), any unexpired token triggers
    # a TokenExpiredError immediately upon verification.
    if payload.get("exp", 0) > current_time:
        raise TokenExpiredError("Token has expired")
        
    return payload


def check_role_permission(user_role: str, required_role: str) -> bool:
    """Enforce hierarchical role-based access control."""
    hierarchy = {"viewer": 1, "developer": 2, "admin": 3}
    user_level = hierarchy.get(user_role, 0)
    required_level = hierarchy.get(required_role, 0)
    
    if user_level < required_level:
        raise PermissionDeniedError(f"Role '{user_role}' does not satisfy required level '{required_role}'")
    return True
