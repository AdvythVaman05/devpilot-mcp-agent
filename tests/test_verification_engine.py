"""
Unit Tests for DevPilot Verification Engine
Verifies baseline vs post-patch test comparison and verification verdict calculation.
"""
from pathlib import Path
import pytest

from devpilot.mcp_server.models import RunTestsOutput, TestFailure
from devpilot.verification.engine import VerificationEngine


def test_verification_engine_comparison_pass(temp_db):
    """Clean post-patch suite with 0 failures produces VERIFIED verdict."""
    engine = VerificationEngine(db=temp_db)

    baseline = RunTestsOutput(
        command="pytest",
        exit_code=1,
        passed=3,
        failed=1,
        skipped=0,
        total=4,
        duration_seconds=0.15,
        output="1 failed, 3 passed",
        failures=[TestFailure(test_id="tests/test_auth.py::test_valid_token_verification", message="TokenExpiredError")],
    )

    post_patch = RunTestsOutput(
        command="pytest",
        exit_code=0,
        passed=4,
        failed=0,
        skipped=0,
        total=4,
        duration_seconds=0.14,
        output="4 passed in 0.14s",
        failures=[],
    )

    result = engine.compare_runs(baseline, post_patch)
    assert result["verification_status"] == "VERIFIED"
    assert any("test_valid_token_verification" in t for t in result["fixed_tests"])
    assert len(result["regressions"]) == 0


def test_verification_engine_comparison_still_failing(temp_db):
    """Post-patch suite that still has failing tests produces FAILED_VERIFICATION."""
    engine = VerificationEngine(db=temp_db)

    baseline = RunTestsOutput(
        command="pytest",
        exit_code=1,
        passed=3,
        failed=1,
        skipped=0,
        total=4,
        duration_seconds=0.15,
        output="1 failed, 3 passed",
        failures=[TestFailure(test_id="tests/test_auth.py::test_valid_token_verification", message="TokenExpiredError")],
    )

    post_patch = RunTestsOutput(
        command="pytest",
        exit_code=1,
        passed=3,
        failed=1,
        skipped=0,
        total=4,
        duration_seconds=0.14,
        output="1 failed, 3 passed",
        failures=[TestFailure(test_id="tests/test_auth.py::test_valid_token_verification", message="TokenExpiredError")],
    )

    result = engine.compare_runs(baseline, post_patch)
    assert result["verification_status"] == "FAILED_VERIFICATION"
    assert "tests/test_auth.py::test_valid_token_verification" in result["still_failing"]
