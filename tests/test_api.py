"""
Unit & Integration Tests for DevPilot FastAPI Endpoints
"""
import pytest
from fastapi.testclient import TestClient

from devpilot.api.app import app
from devpilot.db.database import get_db


def test_api_health(api_client):
    """GET /api/health returns ok status."""
    res = api_client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert "protocol" in data


def test_api_repositories(api_client):
    """GET /api/repositories returns list of repos including sample repo."""
    res = api_client.get("/api/repositories")
    assert res.status_code == 200
    data = res.json()
    assert len(data["repositories"]) >= 1
    assert data["repositories"][0]["id"] == "sample_auth_service"


def test_api_session_lifecycle(api_client, temp_repo):
    """POST /api/sessions creates session and GET /api/sessions retrieves it."""
    res = api_client.post("/api/sessions", json={
        "task": "Investigate auth expiration bug",
        "repo_path": str(temp_repo),
    })
    assert res.status_code == 200
    session_id = res.json()["session_id"]

    res_get = api_client.get(f"/api/sessions/{session_id}")
    assert res_get.status_code == 200
    detail = res_get.json()
    assert detail["session"]["id"] == session_id
    assert detail["session"]["status"] == "INITIALIZING"


def test_api_patch_reject(api_client, temp_repo):
    """POST /api/sessions/{session_id}/patches/{patch_id}/reject marks patch rejected."""
    import uuid
    db = get_db()
    session_id = f"test_api_reject_sess_{uuid.uuid4().hex[:8]}"
    patch_id = f"patch_reject_{uuid.uuid4().hex[:6]}"
    db.create_session(session_id, str(temp_repo), "Task")
    db.create_patch(
        patch_id=patch_id,
        session_id=session_id,
        target_file="auth_service/auth.py",
        diff="--- a\n+++ b",
        rationale="Invalid approach",
        approval_token="tok_reject",
    )

    res = api_client.post(
        f"/api/sessions/{session_id}/patches/{patch_id}/reject",
        json={"reason": "Diff is malformed"}
    )
    assert res.status_code == 200
    assert res.json()["status"] == "REJECTED"


def test_api_demo_reset(api_client):
    """POST /api/demo/reset restores sample repo without errors."""
    res = api_client.post("/api/demo/reset")
    assert res.status_code == 200
    assert res.json()["status"] == "RESET_SUCCESSFUL"
