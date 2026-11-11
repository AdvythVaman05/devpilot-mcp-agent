# Agent Orchestration & Lifecycle Workflow

## 1. Overview

DevPilot organizes autonomous software engineering investigations into a structured, observable, and verifiable **10-Stage Pipeline**. Rather than treating the agent as an opaque black box that returns an unchecked code blob, DevPilot emits real-time events for every stage transition, thought process, and tool invocation.

---

## 2. The 10-Stage Investigation Pipeline

| Stage # | Stage Name | Description | Evidence Captured |
| :--- | :--- | :--- | :--- |
| **Stage 1** | **Initializing agent and provider** | Validates runtime configuration, checks API key requirements, and instantiates the provider (Demo Mock vs Live Gemini). | Provider identification, latency, and credential validation status. |
| **Stage 2** | **Connecting to the MCP server** | Launches the MCP server as an isolated stdio subprocess and completes the protocol handshake. | Subprocess PID, protocol version (`2.x`), and transport confirmation. |
| **Stage 3** | **Discovering available tools** | Introspects registered MCP tools and their input schemas via `session.list_tools()`. | List of discovered tools (8 tools) and parameter schemas. |
| **Stage 4** | **Running baseline tests** | Executes the repository test suite via `run_tests` to establish the baseline failure state. | Exit code (e.g., 1), failing test node IDs, and error tracebacks. |
| **Stage 5** | **Inspecting repository files and failing tests** | Uses `inspect_repository`, `search_code`, and `read_file` to locate the failure origin. | File paths, line numbers, and relevant code excerpts. |
| **Stage 6** | **Identifying the root cause** | Analyzes the inspected code against failing assertions to isolate the exact defect. | Root cause diagnosis statement (e.g., inverted comparison operator). |
| **Stage 7** | **Preparing a proposed patch** | Synthesizes a minimal unified diff and calls `propose_patch` to generate a cryptographic approval token. | Patch ID, target file, unified diff preview, and SHA-256 token. |
| **Stage 8** | **Waiting for human approval** | **Execution is halted.** The backend write guard blocks any filesystem modifications until the user confirms the token. | `AWAITING_APPROVAL` status banner and token verification challenge. |
| **Stage 9** | **Applying the approved patch** | The backend `ApprovalEngine` validates the token and applies the patch directly to the target file. | Timestamp of approval, applied file path, and byte write confirmation. |
| **Stage 10** | **Running post-patch verification** | The `VerificationEngine` re-runs Pytest to confirm the failing test is resolved and zero regressions occurred. | Exit code (0), passing test counts (4/4), and `VERIFIED` report status. |

---

## 3. End-to-End Execution Sequence Diagram

```mermaid
sequenceDiagram
    autonumber
    actor User as Developer / Reviewer
    participant UI as React Frontend Dashboard
    participant API as FastAPI Gateway
    participant Orch as Agent Orchestrator
    participant Mock as Provider Layer (Mock / Gemini)
    participant MCP as MCP Client & Server (stdio)
    participant Appr as Approval Engine
    participant Verif as Verification Engine

    User->>UI: Click "Launch Agent"
    UI->>API: POST /api/sessions (task description)
    API-->>UI: 200 OK (session_id)
    UI->>API: GET /api/sessions/{id}/stream (SSE subscription)
    UI->>API: POST /api/sessions/{id}/investigate
    API->>Orch: Start background worker

    Note over Orch,MCP: Stage 1-3: Initialization & Discovery
    Orch->>API: Emit Stage 1 (Initializing provider)
    Orch->>MCP: connect() (Stage 2: Stdio session)
    Orch->>MCP: discover_tools() (Stage 3: 8 tools discovered)

    Note over Orch,MCP: Stage 4-5: Diagnostics & Code Inspection
    Orch->>Mock: Generate next step
    Mock-->>Orch: ToolCall: run_tests ("pytest -v")
    Orch->>MCP: call_tool("run_tests")
    MCP-->>Orch: Exit code 1 (test_valid_token_verification failed)
    Orch->>API: Emit Stage 4 (Baseline captured)

    Orch->>Mock: Generate next step (with test failure context)
    Mock-->>Orch: ToolCall: search_code ("TokenExpiredError")
    Orch->>MCP: call_tool("search_code")
    MCP-->>Orch: Found match in auth_service/auth.py:88

    Orch->>Mock: Generate next step
    Mock-->>Orch: ToolCall: read_file ("auth_service/auth.py", lines 70-105)
    Orch->>MCP: call_tool("read_file")
    MCP-->>Orch: Returns file source lines
    Orch->>API: Emit Stage 5 & 6 (Code inspected, root cause identified)

    Note over Orch,Appr: Stage 7-8: Patch Proposal & Human Gate
    Orch->>Mock: Generate next step
    Mock-->>Orch: ToolCall: propose_patch (target, diff, rationale)
    Orch->>MCP: call_tool("propose_patch")
    MCP-->>Orch: Returns patch_id & SHA-256 approval_token
    Orch->>API: Emit Stage 7 (Patch proposed)
    Orch->>Orch: Halt loop, set status AWAITING_APPROVAL
    Orch->>API: Emit Stage 8 (Waiting for human approval)

    Note over User,Appr: Human-in-the-Loop Decision
    UI->>User: Render PatchApprovalCard (diff + token)
    User->>UI: Click "Approve & Apply Patch"
    UI->>API: POST /api/sessions/{id}/patches/{id}/approve (token)
    API->>Appr: apply_patch(patch_id, token)
    Appr->>Appr: Verify token constant-time (hmac.compare_digest)
    Appr->>Appr: Write unified diff to disk
    API->>Orch: Emit Stage 9 (Patch applied)

    Note over API,Verif: Stage 10: Verification Engine
    API->>Verif: verify_fix(session_id, repo_root)
    Verif->>Verif: Execute post-patch pytest
    Verif-->>API: 4 passed / 0 failed (Status: VERIFIED)
    API->>Orch: Emit Stage 10 (Verification completed)
    API-->>UI: Final Engineering Report synthesized
```

---

## 4. Real-Time Observability (Server-Sent Events)

DevPilot implements real-time event streaming via `GET /api/sessions/{session_id}/stream`:

1. **`snapshot` Event:** Sent immediately upon connection. Contains the current state of the session, stages, events, tool calls, patches, test runs, and reports.
2. **`stage_update` Event:** Fired whenever one of the 10 stages transitions (`running`, `completed`, `failed`). Includes stage durations and evidence strings.
3. **`execution_event` Event:** Chronological log entries categorized as `AGENT`, `MCP`, `TOOL`, `TEST`, `APPROVAL`, or `ERROR`.
4. **`agent_thought` Event:** Broadcasts the model's reasoning text. Explicitly flags whether the reasoning is simulated (`is_simulated: true`) or live.
5. **`tool_invoking` & `tool_result` Events:** Streams tool parameter payloads and execution results as they happen.

A client polling fallback is built into the dashboard (`pollSession`) to ensure updates continue even if the SSE connection drops or is interrupted by intermediate proxies.

---

## 5. Engineering Report Synthesis

When an investigation reaches verified completion, DevPilot generates a structured Markdown report stored in the `reports` table:
- **Executive Summary:** High-level problem statement and resolution status.
- **Root Cause Analysis:** Technical diagnosis of the failure mechanism.
- **Tool Invocations Audit:** Table of all MCP tools executed, their status, and durations.
- **Patch Details:** Unified diff applied and cryptographic token hash.
- **Verification Evidence:** Baseline vs post-patch Pytest metrics confirming zero regressions.
