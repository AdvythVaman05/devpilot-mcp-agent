"""
Automated Tests for DevPilot Provider Modes, Stage Progression, and Configuration API
"""
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient

from devpilot.agent.orchestrator import AgentOrchestrator
from devpilot.config import settings
from devpilot.db.database import get_db
from devpilot.api.app import app


@pytest.fixture
def client():
    return TestClient(app)


def test_missing_gemini_key_fails_live_mode():
    """Live Gemini mode without an API key must reject execution with explicit error."""
    orchestrator = AgentOrchestrator(
        session_id="test_missing_key",
        api_key="",
        provider_mode="live",
    )
    with pytest.raises(ValueError) as exc:
        import asyncio
        asyncio.run(orchestrator.run_investigation("Investigate test failure"))
    assert "GEMINI_API_KEY is required for Live Gemini mode" in str(exc.value)

    # Check that Stage 1 was marked failed
    db = get_db()
    stages = db.get_stages("test_missing_key")
    stage_1 = next((s for s in stages if s["stage_id"] == 1), None)
    assert stage_1 is not None
    assert stage_1["status"] == "failed"


def test_demo_mode_labels_simulated_reasoning():
    """Demo mode must clearly label simulated model reasoning."""
    orchestrator = AgentOrchestrator(
        session_id="test_demo_label",
        api_key="",
        provider_mode="demo",
    )
    assert orchestrator.use_mock is True
    # Test that next step contains the simulated marker
    res = orchestrator.mock_provider.generate_next_step([])
    assert "[SIMULATED REASONING - DEMO MODE]" in (res.text or "")


def test_api_config_endpoints(client):
    """Verifies GET /api/config and POST /api/config/set-mode."""
    # 1. Get config
    res = client.get("/api/config")
    assert res.status_code == 200
    data = res.json()
    assert "provider_mode" in data
    assert "gemini_model" in data
    assert "protocol" in data

    # 2. Set mode to demo
    res = client.post("/api/config/set-mode", json={"provider_mode": "demo"})
    assert res.status_code == 200
    assert res.json()["provider_mode"] == "demo"

    # 3. Invalid mode
    res = client.post("/api/config/set-mode", json={"provider_mode": "invalid_mode"})
    assert res.status_code == 400


def test_api_test_gemini_missing_key(client):
    """POST /api/config/test-gemini returns error when no key provided."""
    res = client.post("/api/config/test-gemini", json={"api_key": ""})
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is False
    assert data["error_type"] == "MISSING_KEY"


def test_api_test_gemini_invalid_key(client):
    """POST /api/config/test-gemini handles invalid API key without crashing."""
    res = client.post("/api/config/test-gemini", json={"api_key": "invalid_dummy_key_12345"})
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is False
    assert data["error_type"] in ("AUTH_ERROR", "UNKNOWN")
    assert "latency_ms" in data


def test_10_stages_and_events_in_session_details(client):
    """Full session details must return stages and execution events."""
    # Create session
    create_res = client.post("/api/sessions", json={"task": "Verify stages schema"})
    assert create_res.status_code == 200
    session_id = create_res.json()["session_id"]

    # Record some stages and events manually to test retrieval
    db = get_db()
    db.record_stage(
        session_id=session_id,
        stage_id=1,
        name="Initializing agent and provider",
        status="completed",
        explanation="Agent ready",
        evidence="Mock provider",
        duration_seconds=0.1,
    )
    db.record_event(
        session_id=session_id,
        category="AGENT",
        title="Agent Started",
        detail="Testing stages",
        status="info",
    )

    # Get details
    get_res = client.get(f"/api/sessions/{session_id}")
    assert get_res.status_code == 200
    details = get_res.json()
    assert "stages" in details
    assert len(details["stages"]) >= 1
    assert details["stages"][0]["stage_id"] == 1
    assert "events" in details
    assert len(details["events"]) >= 1
    assert details["events"][0]["category"] == "AGENT"
