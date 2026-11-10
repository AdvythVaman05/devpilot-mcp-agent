"""
Integration Tests for DevPilot Agent Orchestrator
Verifies autonomous multi-turn planning, tool dispatching, and mock Gemini fallback.
"""
from pathlib import Path
import pytest

from devpilot.agent.orchestrator import AgentOrchestrator, _clean_schema_for_gemini


def test_schema_cleaning_for_gemini():
    """Confirms OpenAPI schemas are properly normalized for Gemini."""
    dirty_schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "ConfigSchema",
        "type": "object",
        "properties": {
            "query": {"type": "string", "title": "QueryString"},
            "limit": {"type": "integer", "default": 10},
        },
        "required": ["query"],
    }
    cleaned = _clean_schema_for_gemini(dirty_schema)
    assert "$schema" not in cleaned
    assert "title" not in cleaned
    assert cleaned["type"] == "OBJECT"
    assert cleaned["properties"]["query"]["type"] == "STRING"
    assert cleaned["properties"]["limit"]["type"] == "INTEGER"


@pytest.mark.asyncio
async def test_agent_orchestrator_investigation(temp_repo):
    """Orchestrator discovers tools, plans steps, establishes baseline, and pauses at approval."""
    import uuid
    events = []
    def on_event(ev_type, data):
        events.append((ev_type, data))

    session_id = f"test_orch_{uuid.uuid4().hex[:8]}"
    agent = AgentOrchestrator(
        repo_root=temp_repo,
        session_id=session_id,
        use_mock=True,
        on_event=on_event,
    )

    try:
        res = await agent.run_investigation("Diagnose failing auth test and propose fix")
        assert res["status"] == "AWAITING_APPROVAL"
        patch = res["proposed_patch"]
        assert patch is not None
        assert patch["target_file"] == "auth_service/auth.py"
        assert patch["status"] == "PENDING_APPROVAL"
        assert len(patch["approval_token"]) == 64

        # Confirm events were emitted
        event_types = [e[0] for e in events]
        assert "tools_discovered" in event_types
        assert "session_started" in event_types
        assert "tool_invoking" in event_types
        assert "patch_proposed" in event_types

    finally:
        await agent.shutdown()
