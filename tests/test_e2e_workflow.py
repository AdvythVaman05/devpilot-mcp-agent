"""
End-to-End Workflow Test for DevPilot
Simulates the entire real-world lifecycle:
1. Baseline test suite execution (demonstrating intentional failure)
2. MCP tool discovery and autonomous investigation
3. Inverted comparison operator diagnosed in auth_service/auth.py
4. Patch proposed and halted at AWAITING_APPROVAL
5. Human authorization granted via approval token
6. Patch applied to filesystem
7. Post-patch verification test suite executed (4/4 passing)
8. Evidence-backed markdown engineering report synthesized and saved to SQLite
"""
from pathlib import Path
import pytest

from devpilot.agent.orchestrator import AgentOrchestrator
from devpilot.db.database import get_db


@pytest.mark.asyncio
async def test_complete_e2e_investigation_and_verification_lifecycle(temp_repo):
    """Executes the full end-to-end investigation and verification workflow."""
    import uuid
    session_id = f"e2e_{uuid.uuid4().hex[:8]}"
    db = get_db()

    agent = AgentOrchestrator(
        repo_root=temp_repo,
        session_id=session_id,
        use_mock=True,
    )

    try:
        # Phase 1: Autonomous Investigation
        investigation = await agent.run_investigation("Fix failing authentication token expiration test")
        assert investigation["status"] == "AWAITING_APPROVAL"

        patch = investigation["proposed_patch"]
        assert patch["target_file"] == "auth_service/auth.py"
        assert patch["status"] == "PENDING_APPROVAL"

        # Check DB audit trace at approval pause
        session_rec = db.get_session(session_id)
        assert session_rec["status"] == "AWAITING_APPROVAL"

        tool_calls = db.get_tool_calls(session_id)
        tool_names = [tc["tool_name"] for tc in tool_calls]
        assert "run_tests" in tool_names
        assert "search_code" in tool_names
        assert "read_file" in tool_names
        assert "propose_patch" in tool_names

        # Phase 2: Human Approval & Verification
        verification = await agent.execute_approved_patch_and_verify(
            patch_id=patch["patch_id"],
            approval_token=patch["approval_token"],
        )

        assert verification["status"] == "COMPLETED"
        assert verification["verification"]["verification_status"] == "VERIFIED"
        assert "report_markdown" in verification
        assert "DevPilot Engineering Investigation Report" in verification["report_markdown"]

        # Confirm post-patch tests pass on disk
        target_file = temp_repo / "auth_service" / "auth.py"
        with open(target_file, "r", encoding="utf-8") as f:
            content = f.read()
        assert 'if payload.get("exp", 0) < current_time:' in content

        # Verify DB records
        report = db.get_report(session_id)
        assert report is not None
        assert report["verification_status"] == "VERIFIED"

    finally:
        await agent.shutdown()
