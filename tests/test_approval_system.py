"""
Unit Tests for DevPilot Human Approval System
Verifies backend authorization enforcement, token validation, and patch lifecycle.
"""
from pathlib import Path
import pytest

from devpilot.approval.engine import ApprovalEngine
from devpilot.security import UnauthorizedWriteError


def test_unauthorized_patch_application_fails(temp_repo, temp_db):
    """Calling approve_and_apply with invalid token must be rejected."""
    engine = ApprovalEngine(db=temp_db)
    temp_db.create_session("sess_auth_1", str(temp_repo), "Task 1")
    temp_db.create_patch(
        patch_id="patch_101",
        session_id="sess_auth_1",
        target_file="auth_service/auth.py",
        diff="--- a\n+++ b",
        rationale="Fix logic",
        approval_token="valid_secret_token_12345",
    )

    with pytest.raises(UnauthorizedWriteError) as exc_info:
        engine.approve_and_apply(
            patch_id="patch_101",
            approval_token="wrong_token_attempt",
            repo_root=temp_repo,
        )
    assert "Invalid approval token" in str(exc_info.value)


def test_authorized_patch_application_succeeds(temp_repo, temp_db):
    """Valid approval token authorizes write and modifies source file cleanly."""
    engine = ApprovalEngine(db=temp_db)
    temp_db.create_session("sess_auth_2", str(temp_repo), "Task 2")

    # Real patch for the intentional bug
    diff = (
        "--- a/auth_service/auth.py\n"
        "+++ b/auth_service/auth.py\n"
        "@@ -88,3 +88,3 @@\n"
        "-    if payload.get(\"exp\", 0) > current_time:\n"
        "+    if payload.get(\"exp\", 0) < current_time:\n"
    )
    token = "crypto_token_valid_999"

    temp_db.create_patch(
        patch_id="patch_102",
        session_id="sess_auth_2",
        target_file="auth_service/auth.py",
        diff=diff,
        rationale="Fix expiration comparison logic",
        approval_token=token,
    )

    res = engine.approve_and_apply(
        patch_id="patch_102",
        approval_token=token,
        repo_root=temp_repo,
    )

    assert res["status"] == "APPLIED"
    assert res["patch_id"] == "patch_102"

    # Verify file content on disk was actually updated
    target_path = temp_repo / "auth_service" / "auth.py"
    with open(target_path, "r", encoding="utf-8") as f:
        new_content = f.read()

    assert 'if payload.get("exp", 0) < current_time:' in new_content

    # Double apply must be rejected
    with pytest.raises(UnauthorizedWriteError):
        engine.approve_and_apply(
            patch_id="patch_102",
            approval_token=token,
            repo_root=temp_repo,
        )


def test_patch_rejection(temp_repo, temp_db):
    """Rejecting a patch marks it REJECTED and forbids modification."""
    engine = ApprovalEngine(db=temp_db)
    temp_db.create_session("sess_auth_3", str(temp_repo), "Task 3")
    temp_db.create_patch(
        patch_id="patch_103",
        session_id="sess_auth_3",
        target_file="auth_service/auth.py",
        diff="--- a\n+++ b",
        rationale="Bad patch",
        approval_token="tok_103",
    )

    res = engine.reject_patch("patch_103", reason="Approach is incorrect")
    assert res["status"] == "REJECTED"
    assert res["reason"] == "Approach is incorrect"

    patch_record = temp_db.get_patch("patch_103")
    assert patch_record["status"] == "REJECTED"

    # Subsequent approval attempt must be blocked
    with pytest.raises(UnauthorizedWriteError):
        engine.approve_and_apply("patch_103", "tok_103", temp_repo)
