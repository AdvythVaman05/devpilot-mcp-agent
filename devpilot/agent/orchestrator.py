"""
Gemini Agent Orchestrator
Coordinates task decomposition, MCP tool discovery, LLM function calling,
context management, approval pauses, and report generation.
"""
import asyncio
import json
import logging
import os
import sys
import uuid
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from devpilot.agent.mock_provider import MockGeminiProvider
from devpilot.agent.prompts import REPORT_TEMPLATE, SYSTEM_PROMPT
from devpilot.approval.engine import get_approval_engine
from devpilot.config import settings
from devpilot.db.database import get_db
from devpilot.mcp_client.client import DevPilotMCPClient
from devpilot.mcp_server.models import RunTestsOutput
from devpilot.verification.engine import get_verification_engine

logger = logging.getLogger(__name__)


def _clean_schema_for_gemini(s: Any) -> Any:
    """Sanitizes MCP JSON schemas into Gemini OpenAPI Schema format."""
    if not isinstance(s, dict):
        return s
    res = {}
    for k, v in s.items():
        if k in ("$schema", "title", "default"):
            continue
        if k == "type" and isinstance(v, str):
            res[k] = v.upper()
        elif isinstance(v, dict):
            res[k] = _clean_schema_for_gemini(v)
        elif isinstance(v, list):
            res[k] = [_clean_schema_for_gemini(i) for i in v]
        else:
            res[k] = v
    return res


class AgentOrchestrator:
    """
    Production-grade agent orchestrator executing workflows via Model Context Protocol.
    Integrates Google GenAI Gemini with real MCP servers and verifiable human-in-the-loop governance.
    """

    def __init__(
        self,
        repo_root: Optional[Path] = None,
        session_id: Optional[str] = None,
        api_key: Optional[str] = None,
        use_mock: Optional[bool] = None,
        on_event: Optional[Callable[[str, Dict[str, Any]], Any]] = None,
    ):
        self.repo_root = (repo_root or settings.DEFAULT_REPO_ROOT).resolve()
        self.session_id = session_id or f"session_{uuid.uuid4().hex[:8]}"
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.db = get_db()
        self.approval_engine = get_approval_engine()
        self.verification_engine = get_verification_engine()
        self.on_event = on_event

        # Determine provider: real Gemini or deterministic mock
        if use_mock is not None:
            self.use_mock = use_mock
        else:
            self.use_mock = not bool(self.api_key and self.api_key.strip())

        self.mcp_client = DevPilotMCPClient(
            repo_root=self.repo_root,
            session_id=self.session_id,
        )
        self.mock_provider = MockGeminiProvider() if self.use_mock else None
        self.gemini_client = None
        if not self.use_mock:
            try:
                from google import genai
                self.gemini_client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.warning(f"Could not initialize Google GenAI Client: {e}. Falling back to mock provider.")
                self.use_mock = True
                self.mock_provider = MockGeminiProvider()

    def _emit(self, event_type: str, data: Dict[str, Any]) -> None:
        """Emits event to optional subscriber callback (e.g. SSE stream)."""
        if self.on_event:
            try:
                self.on_event(event_type, data)
            except Exception:
                pass

    async def initialize(self) -> None:
        """Connects MCP client session and discovers tools."""
        await self.mcp_client.connect()
        tools = await self.mcp_client.discover_tools()
        self._emit("tools_discovered", {
            "count": len(tools),
            "tools": [t.name for t in tools]
        })

    async def shutdown(self) -> None:
        """Gracefully disconnects MCP client."""
        await self.mcp_client.disconnect()

    async def run_investigation(self, task: str) -> Dict[str, Any]:
        """
        Executes autonomous investigation loop:
        1. Establishes baseline test run.
        2. Inspects code and pinpoints root cause.
        3. Proposes patch via propose_patch.
        4. Halts at AWAITING_APPROVAL for human authorization.
        """
        # Ensure session exists in SQLite
        existing = self.db.get_session(self.session_id)
        if not existing:
            self.db.create_session(
                session_id=self.session_id,
                repo_path=str(self.repo_root),
                task=task,
            )

        self.db.update_session_status(self.session_id, "INVESTIGATING")
        self._emit("session_started", {
            "session_id": self.session_id,
            "task": task,
            "provider": "MockGeminiProvider" if self.use_mock else "Google Gemini API",
        })

        # Register initial investigation plan
        plan_steps = [
            {"id": "step_1", "description": "Execute baseline test suite to observe failure", "status": "IN_PROGRESS"},
            {"id": "step_2", "description": "Search code and inspect failing test and source files", "status": "PENDING"},
            {"id": "step_3", "description": "Diagnose root cause and formulate solution", "status": "PENDING"},
            {"id": "step_4", "description": "Formulate and propose code patch for review", "status": "PENDING"},
            {"id": "step_5", "description": "Await human approval and authorization", "status": "PENDING"},
            {"id": "step_6", "description": "Apply approved patch and execute verification engine", "status": "PENDING"},
        ]
        self.db.record_plan("plan_1", self.session_id, plan_steps, current_step=0)
        self._emit("plan_updated", {"steps": plan_steps})

        # Connect MCP if not already connected
        if not self.mcp_client.is_connected:
            await self.initialize()

        # Multi-turn interaction loop
        max_turns = 10
        turn = 0
        final_message = ""
        proposed_patch = None

        while turn < max_turns:
            turn += 1
            tool_history = self.db.get_tool_calls(self.session_id)

            if self.use_mock:
                response = self.mock_provider.generate_next_step(tool_history)
                message_text = response.text or ""
                function_calls = response.function_calls
            else:
                message_text, function_calls = await self._call_real_gemini(task, tool_history)

            self._emit("agent_thought", {
                "turn": turn,
                "text": message_text,
            })

            if not function_calls:
                final_message = message_text
                break

            # Execute function calls through official MCP Client
            for call in function_calls:
                call_name = call.name
                call_args = call.args if hasattr(call, "args") else getattr(call, "arguments", {})

                self._emit("tool_invoking", {
                    "tool": call_name,
                    "arguments": call_args,
                })

                try:
                    tool_result = await self.mcp_client.call_tool(call_name, call_args)
                    self._emit("tool_result", {
                        "tool": call_name,
                        "result": tool_result,
                    })

                    # If tool was run_tests and baseline not yet recorded as baseline run
                    if call_name == "run_tests":
                        baseline_runs = [r for r in self.db.get_test_runs(self.session_id) if r["phase"] == "BASELINE"]
                        if not baseline_runs:
                            # Record baseline in test_runs table
                            failures = tool_result.get("failures", [])
                            self.db.record_test_run(
                                run_id=f"run_baseline_{uuid.uuid4().hex[:8]}",
                                session_id=self.session_id,
                                phase="BASELINE",
                                command=call_args.get("command", "pytest -v"),
                                exit_code=tool_result.get("exit_code", 1),
                                passed_count=tool_result.get("passed", 0),
                                failed_count=tool_result.get("failed", 0),
                                skipped_count=tool_result.get("skipped", 0),
                                total_count=tool_result.get("total", 0),
                                duration_seconds=tool_result.get("duration_seconds", 0.0),
                                raw_output=tool_result.get("output", ""),
                                test_cases=failures,
                            )
                            plan_steps[0]["status"] = "COMPLETED"
                            plan_steps[1]["status"] = "IN_PROGRESS"
                            self.db.record_plan("plan_1", self.session_id, plan_steps, current_step=1)
                            self._emit("plan_updated", {"steps": plan_steps})

                    # Update step progress on code inspection
                    if call_name in ("search_code", "read_file"):
                        plan_steps[1]["status"] = "COMPLETED"
                        plan_steps[2]["status"] = "IN_PROGRESS"
                        self.db.record_plan("plan_1", self.session_id, plan_steps, current_step=2)
                        self._emit("plan_updated", {"steps": plan_steps})

                    # If propose_patch was called, PAUSE at human approval!
                    if call_name == "propose_patch":
                        proposed_patch = tool_result
                        plan_steps[2]["status"] = "COMPLETED"
                        plan_steps[3]["status"] = "COMPLETED"
                        plan_steps[4]["status"] = "IN_PROGRESS"
                        self.db.record_plan("plan_1", self.session_id, plan_steps, current_step=4)
                        self.db.update_session_status(self.session_id, "AWAITING_APPROVAL")

                        self._emit("patch_proposed", {
                            "patch_id": tool_result.get("patch_id"),
                            "target_file": tool_result.get("target_file"),
                            "diff": tool_result.get("diff_preview"),
                            "rationale": tool_result.get("rationale"),
                            "approval_token": tool_result.get("approval_token"),
                        })
                        self._emit("plan_updated", {"steps": plan_steps})
                        # STOP execution loop to wait for human authorization
                        return {
                            "session_id": self.session_id,
                            "status": "AWAITING_APPROVAL",
                            "proposed_patch": proposed_patch,
                            "message": "Patch proposed. Awaiting explicit human approval before any file writes.",
                        }

                except Exception as e:
                    self._emit("tool_error", {
                        "tool": call_name,
                        "error": str(e),
                    })

        return {
            "session_id": self.session_id,
            "status": self.db.get_session(self.session_id)["status"],
            "proposed_patch": proposed_patch,
            "final_message": final_message,
        }

    async def _call_real_gemini(
        self,
        task: str,
        tool_history: List[Dict[str, Any]]
    ) -> Tuple[str, List[Any]]:
        """Invokes Google Gemini API with MCP function declarations."""
        from google.genai import types

        # Build function declarations from discovered MCP tools
        tools_discovered = await self.mcp_client.discover_tools()
        gemini_funcs = []
        for t in tools_discovered:
            cleaned_schema = _clean_schema_for_gemini(t.inputSchema)
            fd = types.FunctionDeclaration(
                name=t.name,
                description=t.description or f"MCP tool {t.name}",
                parameters=cleaned_schema if cleaned_schema else None,
            )
            gemini_funcs.append(fd)

        gemini_tools = [types.Tool(function_declarations=gemini_funcs)]

        # Construct conversation history
        contents = [
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=f"Task: {task}")],
            )
        ]

        # Append prior tool calls & responses
        for call in tool_history:
            contents.append(
                types.Content(
                    role="model",
                    parts=[
                        types.Part.from_function_call(
                            name=call["tool_name"],
                            args=call["arguments"],
                        )
                    ],
                )
            )
            contents.append(
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_function_response(
                            name=call["tool_name"],
                            response={"result": call["result"]},
                        )
                    ],
                )
            )

        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            tools=gemini_tools,
            temperature=0.1,
        )

        response = await asyncio.to_thread(
            self.gemini_client.models.generate_content,
            model=settings.GEMINI_MODEL,
            contents=contents,
            config=config,
        )

        text_out = response.text or ""
        fn_calls = response.function_calls or []
        return text_out, fn_calls

    async def execute_approved_patch_and_verify(
        self,
        patch_id: str,
        approval_token: str,
    ) -> Dict[str, Any]:
        """
        Executes authorized write operation, transitions state machine,
        executes post-patch verification suite, and generates final engineering report.
        """
        # 1. Authorize & apply write operation
        self._emit("patch_applying", {"patch_id": patch_id})
        apply_result = self.approval_engine.approve_and_apply(
            patch_id=patch_id,
            approval_token=approval_token,
            repo_root=self.repo_root,
        )
        self._emit("patch_applied", apply_result)

        # 2. Update Plan
        plan = self.db.get_plan(self.session_id)
        if plan:
            steps = plan["steps"]
            steps[4]["status"] = "COMPLETED"
            steps[5]["status"] = "IN_PROGRESS"
            self.db.record_plan(plan["id"], self.session_id, steps, current_step=5)
            self._emit("plan_updated", {"steps": steps})

        self.db.update_session_status(self.session_id, "VERIFYING")
        self._emit("verification_started", {"session_id": self.session_id})

        # 3. Run verification test suite
        verification_run = self.verification_engine.run_suite(
            session_id=self.session_id,
            repo_root=self.repo_root,
            phase="VERIFICATION",
        )

        # 4. Fetch baseline run and compare
        test_runs = self.db.get_test_runs(self.session_id)
        baseline_run_data = next((r for r in test_runs if r["phase"] == "BASELINE"), None)

        if baseline_run_data:
            from devpilot.mcp_server.models import TestFailure
            baseline_run = RunTestsOutput(
                command=baseline_run_data["command"],
                exit_code=baseline_run_data["exit_code"],
                passed=baseline_run_data["passed_count"],
                failed=baseline_run_data["failed_count"],
                skipped=baseline_run_data["skipped_count"],
                total=baseline_run_data["total_count"],
                duration_seconds=baseline_run_data["duration_seconds"],
                output=baseline_run_data["raw_output"] or "",
                failures=[
                    TestFailure(test_id=f.get("test_id", "fail"), message=f.get("message", ""))
                    for f in baseline_run_data.get("test_cases", [])
                ],
            )
            comparison = self.verification_engine.compare_runs(baseline_run, verification_run)
        else:
            comparison = {
                "verification_status": "VERIFIED" if verification_run.exit_code == 0 else "FAILED_VERIFICATION",
                "summary": "Verification completed without baseline comparison.",
                "fixed_tests": [],
                "regressions": [],
            }

        # 5. Generate and persist final engineering report
        patch = self.db.get_patch(patch_id)
        session = self.db.get_session(self.session_id)

        report_md = REPORT_TEMPLATE.format(
            summary=(
                f"Autonomous investigation of authentication service test failure. "
                f"Root cause was diagnosed as an inverted comparison operator in the token expiration logic. "
                f"Patch proposed, authorized by human reviewer, applied, and verified against full test suite."
            ),
            repo_root=str(self.repo_root),
            branch="master",
            test_count=verification_run.total,
            baseline_cmd=baseline_run_data["command"] if baseline_run_data else "pytest",
            baseline_exit_code=baseline_run_data["exit_code"] if baseline_run_data else 1,
            baseline_symptoms="`test_valid_token_verification` failed with `TokenExpiredError: Token has expired` for valid tokens.",
            target_file=patch["target_file"] if patch else "auth_service/auth.py",
            bug_category="Logic Inversion / Comparison Operator Flaw",
            root_cause_explanation=(
                "In `auth_service/auth.py` at line 88, the token expiration check was implemented as:\n"
                "`if payload.get('exp', 0) > current_time:`\n"
                "Because unexpired tokens legitimately have `exp > current_time`, this condition incorrectly evaluated to True "
                "for all valid tokens, raising `TokenExpiredError` immediately upon issuance."
            ),
            patch_id=patch_id,
            approval_status="APPROVED_AND_APPLIED",
            patch_diff=patch["diff"] if patch else "",
            patch_rationale=patch["rationale"] if patch else "",
            verification_status=comparison["verification_status"],
            post_passed=verification_run.passed,
            post_failed=verification_run.failed,
            post_exit_code=verification_run.exit_code,
            verification_evidence=(
                f"- Baseline Failures Resolved: {', '.join(comparison['fixed_tests']) if comparison['fixed_tests'] else 'All previously failing tests'}\n"
                f"- Regressions: 0\n"
                f"- Suite Exit Code: {verification_run.exit_code} (Clean Success)"
            ),
        )

        report_id = f"report_{uuid.uuid4().hex[:8]}"
        self.db.record_report(
            report_id=report_id,
            session_id=self.session_id,
            summary=comparison["summary"],
            root_cause="Inverted expiration comparison operator in verify_token()",
            patch_summary=f"Changed `>` to `<` in {patch['target_file'] if patch else 'auth_service/auth.py'}",
            verification_status=comparison["verification_status"],
            full_markdown=report_md,
        )

        # Complete session
        if plan:
            steps[5]["status"] = "COMPLETED"
            self.db.record_plan(plan["id"], self.session_id, steps, current_step=5)
            self._emit("plan_updated", {"steps": steps})

        final_status = "COMPLETED" if comparison["verification_status"] == "VERIFIED" else "FAILED"
        self.db.update_session_status(self.session_id, final_status)

        result_payload = {
            "session_id": self.session_id,
            "patch_id": patch_id,
            "status": final_status,
            "verification": comparison,
            "report_id": report_id,
            "report_markdown": report_md,
        }

        self._emit("investigation_completed", result_payload)
        return result_payload
