# DevPilot Automated Testing Strategy & Verification Guide

DevPilot is accompanied by an automated test suite containing 33 unit and integration tests covering security, protocol compliance, tool correctness, human-in-the-loop governance, and end-to-end workflows.

---

## 1. Running the Automated Test Suite

From the repository root with virtual environment activated:

```bash
# Run the complete test suite with verbose output
python -m pytest tests -v
```

Expected output:
```text
tests/test_agent_orchestrator.py::test_schema_cleaning_for_gemini PASSED
tests/test_agent_orchestrator.py::test_agent_orchestrator_investigation PASSED
tests/test_api.py::test_api_health PASSED
tests/test_api.py::test_api_repositories PASSED
tests/test_api.py::test_api_session_lifecycle PASSED
tests/test_api.py::test_api_patch_reject PASSED
tests/test_api.py::test_api_demo_reset PASSED
tests/test_approval_system.py::test_unauthorized_patch_application_fails PASSED
tests/test_approval_system.py::test_authorized_patch_application_succeeds PASSED
tests/test_approval_system.py::test_patch_rejection PASSED
tests/test_e2e_workflow.py::test_complete_e2e_investigation_and_verification_lifecycle PASSED
tests/test_mcp_client.py::test_mcp_client_connection_and_discovery PASSED
tests/test_mcp_client.py::test_mcp_client_tool_invocation PASSED
tests/test_mcp_server.py::test_inspect_repository PASSED
tests/test_mcp_server.py::test_list_files PASSED
tests/test_mcp_server.py::test_read_file PASSED
tests/test_mcp_server.py::test_read_file_nonexistent_raises PASSED
tests/test_mcp_server.py::test_search_code PASSED
tests/test_mcp_server.py::test_search_code_regex PASSED
tests/test_mcp_server.py::test_run_tests_failure_capture PASSED
tests/test_mcp_server.py::test_run_tests_timeout_handling PASSED
tests/test_mcp_server.py::test_get_git_status PASSED
tests/test_mcp_server.py::test_get_git_diff_clean PASSED
tests/test_mcp_server.py::test_propose_patch_creates_token PASSED
tests/test_security.py::test_path_traversal_rejection_parent_dir PASSED
tests/test_security.py::test_path_traversal_rejection_absolute_path PASSED
tests/test_security.py::test_valid_path_resolution PASSED
tests/test_security.py::test_disallowed_command_rejection PASSED
tests/test_security.py::test_command_injection_operators_rejected PASSED
tests/test_security.py::test_allowlisted_command_accepted PASSED
tests/test_security.py::test_sensitive_data_redaction PASSED
tests/test_verification_engine.py::test_verification_engine_comparison_pass PASSED
tests/test_verification_engine.py::test_verification_engine_comparison_still_failing PASSED

============================= 33 passed in 10.94s =============================
```

---

## 2. Test Architecture & Coverage Matrix

| Test Module | Coverage Scope | Key Assertions Verified |
|---|---|---|
| `test_security.py` | Filesystem sandboxing & command sanitization | Path traversal with `../` and absolute paths rejected; shell operators (`;`, `&&`, `\|`) rejected; secret redaction masks keys and bearer tokens. |
| `test_mcp_server.py` | Individual MCP tool behaviors | `inspect_repository`, `list_files`, `read_file` (ranges and bounds), `search_code` (text/regex), `run_tests` (failure capture & timeout), `get_git_status`, `get_git_diff`, `propose_patch` (token generation without file writes). |
| `test_mcp_client.py` | Genuine MCP protocol client | MCP session handshake over `stdio`; dynamic discovery of all 8 tools; tool execution through client session. |
| `test_approval_system.py` | Backend human-in-the-loop authorization | Rejection of unapproved writes; rejection of invalid/tampered tokens; clean patch application upon authorization; double-apply rejection; patch rejection state. |
| `test_verification_engine.py` | Baseline vs post-patch test comparison | Distinction between `VERIFIED` and `FAILED_VERIFICATION`; detection of regressions; exit code validation. |
| `test_agent_orchestrator.py` | Multi-turn planning & tool dispatch | MCP schema translation to Gemini format; baseline execution; code inspection; pausing at `AWAITING_APPROVAL`. |
| `test_e2e_workflow.py` | Complete end-to-end investigation lifecycle | Full autonomous run: initial test failure $\rightarrow$ code search $\rightarrow$ diagnosis $\rightarrow$ patch proposal $\rightarrow$ approval authorization $\rightarrow$ verification suite $\rightarrow$ report synthesis. |
| `test_api.py` | FastAPI HTTP & REST endpoints | `/api/health`, `/api/repositories`, `/api/sessions`, patch approval/rejection endpoints, `/api/demo/reset`. |

---

## 3. Sample Python Repository (`sample_repo`)

DevPilot includes a real microservice repository in `sample_repo/` with:
- `auth_service/auth.py`: Token encoding/decoding with an intentional comparison operator flaw on line 88:
  ```python
  if payload.get("exp", 0) > current_time:
      raise TokenExpiredError("Token has expired")
  ```
- `tests/test_auth.py`: Pytest suite where 3 tests pass, and 1 test (`test_valid_token_verification`) fails due to this bug.
- Executing `python -m pytest sample_repo/tests -v` returns exit code 1 with 1 failure and 3 passes.
- After the agent's patch is authorized and applied, all 4 tests pass cleanly with exit code 0.
