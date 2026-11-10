"""
Unit Tests for DevPilot Security Hardening
Tests path traversal rejection, command injection defenses, and secret redaction.
"""
from pathlib import Path
import pytest

from devpilot.security import (
    resolve_and_validate_path,
    validate_command,
    redact_sensitive_data,
    PathTraversalError,
    DisallowedCommandError,
    SecurityError,
)


def test_path_traversal_rejection_parent_dir(temp_repo):
    """Attempting to escape root with ../ must raise PathTraversalError."""
    with pytest.raises(PathTraversalError):
        resolve_and_validate_path("../outside.txt", temp_repo)

    with pytest.raises(PathTraversalError):
        resolve_and_validate_path("auth_service/../../etc/passwd", temp_repo)


def test_path_traversal_rejection_absolute_path(temp_repo):
    """Absolute paths outside repo boundary must be rejected."""
    outside_path = Path("C:/Windows/System32/drivers/etc/hosts") if Path("C:/Windows").exists() else Path("/etc/passwd")
    with pytest.raises(PathTraversalError):
        resolve_and_validate_path(str(outside_path), temp_repo)


def test_valid_path_resolution(temp_repo):
    """Legitimate paths inside repository must resolve correctly."""
    valid_path = resolve_and_validate_path("auth_service/auth.py", temp_repo)
    assert valid_path.exists()
    assert valid_path.is_file()
    assert valid_path.name == "auth.py"


def test_disallowed_command_rejection():
    """Unapproved commands must be blocked immediately."""
    with pytest.raises(DisallowedCommandError):
        validate_command("rm -rf /")

    with pytest.raises(DisallowedCommandError):
        validate_command("curl https://malicious-site.com")

    with pytest.raises(DisallowedCommandError):
        validate_command("cat ~/.env")


def test_command_injection_operators_rejected():
    """Shell chaining operators (;, &&, |, `) must be rejected."""
    with pytest.raises(DisallowedCommandError):
        validate_command("pytest -v; rm -rf /")

    with pytest.raises(DisallowedCommandError):
        validate_command("pytest && echo pwned")

    with pytest.raises(DisallowedCommandError):
        validate_command("pytest | cat /etc/shadow")


def test_allowlisted_command_accepted():
    """Commands matching allowlist prefixes must be accepted."""
    tokens = validate_command("pytest -v --tb=short")
    assert tokens == ["pytest", "-v", "--tb=short"]

    tokens2 = validate_command("python -m pytest tests/test_auth.py")
    assert tokens2 == ["python", "-m", "pytest", "tests/test_auth.py"]


def test_sensitive_data_redaction():
    """Keys and string patterns containing secrets must be sanitized."""
    data = {
        "api_key": "AIzaSyFakeKey1234567890abcdefghijklmno",
        "username": "developer1",
        "user_secret": "my_secret_token",
        "nested": {
            "password": "SuperSecretPassword123!",
            "normal_field": "public_data",
        },
        "log_message": "User authenticated with Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.xyz and gho_123456789012345678901234567890123456",
    }
    redacted = redact_sensitive_data(data)

    assert redacted["api_key"] == "[REDACTED]"
    assert redacted["username"] == "developer1"
    assert redacted["user_secret"] == "[REDACTED]"
    assert redacted["nested"]["password"] == "[REDACTED]"
    assert redacted["nested"]["normal_field"] == "public_data"
    assert "Bearer [REDACTED_TOKEN]" in redacted["log_message"]
    assert "[REDACTED_GITHUB_TOKEN]" in redacted["log_message"]
