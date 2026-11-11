"""
DevPilot FastAPI Route Handlers
Provides endpoints for repository management, investigation sessions,
real-time SSE event streaming, human-in-the-loop patch authorization,
provider configuration & connectivity tests, and demo reset.
"""
import asyncio
import json
import logging
import subprocess
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from devpilot.agent.orchestrator import AgentOrchestrator
from devpilot.approval.engine import get_approval_engine
from devpilot.config import settings
from devpilot.db.database import get_db
from devpilot.security import UnauthorizedWriteError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")

# In-memory pub/sub queues for SSE streaming per session
session_subscribers: Dict[str, List[asyncio.Queue]] = {}


def broadcast_event(session_id: str, event_type: str, data: Dict[str, Any]) -> None:
    """Dispatches real-time events to all active SSE subscribers for this session."""
    queues = session_subscribers.get(session_id, [])
    payload = {"type": event_type, "data": data}
    for q in list(queues):
        try:
            q.put_nowait(payload)
        except Exception:
            pass


class CreateSessionRequest(BaseModel):
    task: str = Field(description="Investigation instructions or bug description")
    repo_path: Optional[str] = Field(default=None, description="Path to repository. Defaults to sample_repo")
    api_key: Optional[str] = Field(default=None, description="Optional Google Gemini API key")
    provider_mode: Optional[str] = Field(default=None, description="Optional provider mode: 'live' or 'demo'")


class StartInvestigationRequest(BaseModel):
    api_key: Optional[str] = Field(default=None, description="Optional Google Gemini API key")
    provider_mode: Optional[str] = Field(default=None, description="Optional provider mode: 'live' or 'demo'")


class ApprovePatchRequest(BaseModel):
    approval_token: str = Field(description="Cryptographic approval token matching proposed patch")


class RejectPatchRequest(BaseModel):
    reason: Optional[str] = Field(default="Rejected by user", description="Reason for rejecting the proposed patch")


class TestGeminiRequest(BaseModel):
    api_key: Optional[str] = Field(default=None, description="Gemini API key to test. If omitted, uses configured key.")


class SetModeRequest(BaseModel):
    provider_mode: str = Field(description="'live' or 'demo'")
    api_key: Optional[str] = Field(default=None, description="Optional API key for live mode")


@router.get("/health")
def get_health() -> Dict[str, Any]:
    """System health check and component status."""
    sample_repo_exists = settings.DEFAULT_REPO_ROOT.exists()
    has_api_key = bool(settings.GEMINI_API_KEY and settings.GEMINI_API_KEY.strip())
    
    return {
        "status": "ok",
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "sample_repo_available": sample_repo_exists,
        "provider_mode": settings.PROVIDER_MODE,
        "gemini_api_key_configured": has_api_key,
        "active_provider": f"Google Gemini API ({settings.GEMINI_MODEL})" if (settings.PROVIDER_MODE == "live" and has_api_key) else "Deterministic Mock Provider (Demo Mode)",
        "mcp_server_status": "ready",
        "protocol": "Model Context Protocol (MCP) 2.x",
    }


@router.get("/config")
def get_config() -> Dict[str, Any]:
    """Retrieves current runtime configuration status without exposing sensitive credentials."""
    return {
        "provider_mode": settings.PROVIDER_MODE,
        "gemini_model": settings.GEMINI_MODEL,
        "gemini_api_key_configured": bool(settings.GEMINI_API_KEY and settings.GEMINI_API_KEY.strip()),
        "command_timeout_seconds": settings.COMMAND_TIMEOUT_SECONDS,
        "sample_repo_available": settings.DEFAULT_REPO_ROOT.exists(),
        "protocol": "Model Context Protocol (MCP) 2.x",
    }


@router.post("/config/test-gemini")
async def test_gemini_connection(req: TestGeminiRequest) -> Dict[str, Any]:
    """
    Tests connectivity to Google Gemini API using provided key or configured key.
    Measures latency and returns structured diagnostics without storing or exposing secrets.
    """
    key = req.api_key.strip() if req.api_key else settings.GEMINI_API_KEY
    if not key:
        return {
            "success": False,
            "error_type": "MISSING_KEY",
            "error": "No Gemini API key provided. Enter an API key or switch to Demo Mode.",
        }

    start_time = time.time()
    try:
        from google import genai
        client = genai.Client(api_key=key)
        # Execute lightweight generation test
        await asyncio.to_thread(
            client.models.generate_content,
            model=settings.GEMINI_MODEL,
            contents="Ping",
        )
        latency_ms = round((time.time() - start_time) * 1000)
        return {
            "success": True,
            "model": settings.GEMINI_MODEL,
            "latency_ms": latency_ms,
            "message": f"Successfully verified Google Gemini API connection ({settings.GEMINI_MODEL}).",
        }
    except Exception as e:
        latency_ms = round((time.time() - start_time) * 1000)
        err_str = str(e)
        error_type = "UNKNOWN"
        if "API_KEY_INVALID" in err_str or "unauthenticated" in err_str.lower() or "invalid api key" in err_str.lower():
            error_type = "AUTH_ERROR"
        elif "quota" in err_str.lower() or "429" in err_str or "resource_exhausted" in err_str.lower():
            error_type = "QUOTA_ERROR"
        elif "connection" in err_str.lower() or "timeout" in err_str.lower() or "network" in err_str.lower():
            error_type = "NETWORK_ERROR"

        return {
            "success": False,
            "error_type": error_type,
            "error": err_str,
            "latency_ms": latency_ms,
        }


@router.post("/config/set-mode")
def set_provider_mode(req: SetModeRequest) -> Dict[str, Any]:
    """Switches active provider mode between 'live' and 'demo'."""
    mode = req.provider_mode.lower()
    if mode not in ("live", "demo"):
        raise HTTPException(status_code=400, detail="Invalid provider_mode. Must be 'live' or 'demo'.")

    if mode == "live" and req.api_key:
        settings.GEMINI_API_KEY = req.api_key.strip()

    settings.PROVIDER_MODE = mode
    return {
        "status": "updated",
        "provider_mode": settings.PROVIDER_MODE,
        "gemini_api_key_configured": bool(settings.GEMINI_API_KEY),
    }


@router.get("/repositories")
def list_repositories() -> Dict[str, Any]:
    """Lists preconfigured and accessible repositories."""
    sample_root = settings.DEFAULT_REPO_ROOT
    return {
        "repositories": [
            {
                "id": "sample_auth_service",
                "name": "Sample Authentication Service (Microservice)",
                "path": str(sample_root),
                "is_default": True,
                "has_intentional_bug": True,
                "description": "HMAC-SHA256 JWT service with intentional expiration comparison logic inversion.",
                "failing_test": "tests/test_auth.py::test_valid_token_verification",
            }
        ]
    }


@router.post("/sessions")
async def create_session(req: CreateSessionRequest) -> Dict[str, Any]:
    """Initializes a new engineering investigation session."""
    db = get_db()
    session_id = f"session_{uuid.uuid4().hex[:8]}"

    repo_root = Path(req.repo_path) if req.repo_path else settings.DEFAULT_REPO_ROOT
    if not repo_root.exists():
        raise HTTPException(status_code=400, detail=f"Repository root does not exist: {repo_root}")

    session = db.create_session(
        session_id=session_id,
        repo_path=str(repo_root),
        task=req.task,
    )

    return {
        "session_id": session_id,
        "session": session,
    }


@router.get("/sessions")
def list_sessions(limit: int = 20) -> List[Dict[str, Any]]:
    """Lists past investigation sessions."""
    db = get_db()
    return db.list_sessions(limit=limit)


@router.get("/sessions/{session_id}")
def get_session_details(session_id: str) -> Dict[str, Any]:
    """Retrieves full execution trace, 10-stage pipeline, events, and artifacts for a session."""
    db = get_db()
    session = db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    plan = db.get_plan(session_id)
    stages = db.get_stages(session_id)
    events = db.get_events(session_id)
    tool_calls = db.get_tool_calls(session_id)
    patches = db.get_session_patches(session_id)
    test_runs = db.get_test_runs(session_id)
    report = db.get_report(session_id)

    return {
        "session": session,
        "plan": plan,
        "stages": stages,
        "events": events,
        "tool_calls": tool_calls,
        "patches": patches,
        "test_runs": test_runs,
        "report": report,
    }


async def _run_agent_task(
    session_id: str,
    repo_path: str,
    task: str,
    api_key: Optional[str] = None,
    provider_mode: Optional[str] = None,
):
    """Background worker executing agent investigation loop."""
    def on_event(event_type: str, data: Dict[str, Any]):
        broadcast_event(session_id, event_type, data)

    agent = AgentOrchestrator(
        repo_root=Path(repo_path),
        session_id=session_id,
        api_key=api_key,
        provider_mode=provider_mode,
        on_event=on_event,
    )
    db = get_db()
    try:
        await agent.run_investigation(task)
    except Exception as e:
        logger.error(f"Investigation execution error for session {session_id}: {e}", exc_info=True)
        db.update_session_status(session_id, "FAILED")
        broadcast_event(session_id, "investigation_failed", {
            "session_id": session_id,
            "error": str(e),
        })
    finally:
        await agent.shutdown()


@router.post("/sessions/{session_id}/investigate")
async def start_investigation(
    session_id: str,
    background_tasks: BackgroundTasks,
    req: Optional[StartInvestigationRequest] = None,
) -> Dict[str, Any]:
    """Triggers autonomous investigation loop in the background."""
    db = get_db()
    session = db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    repo_path = session["repository_path"]
    task = session["task_description"]
    api_key = req.api_key if req else None
    provider_mode = req.provider_mode if req else None

    # Run investigation in background
    background_tasks.add_task(_run_agent_task, session_id, repo_path, task, api_key, provider_mode)

    return {
        "session_id": session_id,
        "status": "STARTED",
        "message": "Autonomous MCP investigation started. Connect to SSE stream for live updates.",
    }


@router.get("/sessions/{session_id}/stream")
async def stream_session_events(session_id: str, request: Request) -> EventSourceResponse:
    """Server-Sent Events (SSE) streaming real-time agent execution trace."""
    db = get_db()
    session = db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    queue = asyncio.Queue()
    if session_id not in session_subscribers:
        session_subscribers[session_id] = []
    session_subscribers[session_id].append(queue)

    async def event_generator():
        try:
            # Yield initial snapshot
            yield {
                "event": "snapshot",
                "data": json.dumps(get_session_details(session_id)),
            }

            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=20.0)
                    yield {
                        "event": event["type"],
                        "data": json.dumps(event["data"]),
                    }
                except asyncio.TimeoutError:
                    # Keepalive ping
                    yield {"event": "ping", "data": "{}"}
        finally:
            if session_id in session_subscribers and queue in session_subscribers[session_id]:
                session_subscribers[session_id].remove(queue)

    return EventSourceResponse(event_generator())


@router.post("/sessions/{session_id}/patches/{patch_id}/approve")
async def approve_patch(
    session_id: str,
    patch_id: str,
    req: ApprovePatchRequest,
) -> Dict[str, Any]:
    """
    Human-in-the-Loop Approval Authorization.
    Verifies the cryptographic approval token, applies the patch to the source file,
    executes post-patch verification tests, and synthesizes the final engineering report.
    """
    db = get_db()
    session = db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    repo_root = Path(session["repository_path"])

    def on_event(event_type: str, data: Dict[str, Any]):
        broadcast_event(session_id, event_type, data)

    agent = AgentOrchestrator(
        repo_root=repo_root,
        session_id=session_id,
        on_event=on_event,
    )

    try:
        result = await agent.execute_approved_patch_and_verify(
            patch_id=patch_id,
            approval_token=req.approval_token,
        )
        return result
    except UnauthorizedWriteError as uwe:
        raise HTTPException(status_code=403, detail=str(uwe))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await agent.shutdown()


@router.post("/sessions/{session_id}/patches/{patch_id}/reject")
def reject_patch(
    session_id: str,
    patch_id: str,
    req: RejectPatchRequest,
) -> Dict[str, Any]:
    """Rejects a proposed patch. Enforces that no filesystem changes take place."""
    db = get_db()
    session = db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    approval_engine = get_approval_engine()
    try:
        res = approval_engine.reject_patch(patch_id=patch_id, reason=req.reason)
        # Record stage update and rejection event
        db.record_stage(
            session_id=session_id,
            stage_id=8,
            name="Waiting for human approval",
            status="failed",
            explanation=f"Patch rejected by user: {req.reason}",
            evidence="Write permission denied by reviewer. No repository files modified.",
        )
        db.record_event(
            session_id=session_id,
            category="APPROVAL",
            title="Patch Rejected by Reviewer",
            detail=f"Rejection reason: {req.reason}",
            status="warning",
        )
        db.update_session_status(session_id, "REJECTED")

        broadcast_event(session_id, "patch_rejected", res)
        broadcast_event(session_id, "stage_update", {
            "stage_id": 8,
            "status": "failed",
            "explanation": f"Patch rejected by user: {req.reason}",
            "evidence": "Write permission denied by reviewer. No repository files modified.",
        })
        return res
    except UnauthorizedWriteError as uwe:
        raise HTTPException(status_code=400, detail=str(uwe))


@router.post("/demo/reset")
def reset_sample_repository() -> Dict[str, Any]:
    """
    Restores the sample authentication service repository to its baseline state
    with the intentional expiration bug and failing test.
    """
    from devpilot.mcp_server.tools import ensure_git_repo
    sample_root = settings.DEFAULT_REPO_ROOT
    ensure_git_repo(sample_root)

    try:
        subprocess.run(
            ["git", "checkout", "--", "."],
            cwd=str(sample_root),
            check=True,
            capture_output=True,
            timeout=5,
        )
        return {
            "status": "RESET_SUCCESSFUL",
            "message": "Sample repository restored to baseline state with intentional bug.",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reset sample repository: {str(e)}")
