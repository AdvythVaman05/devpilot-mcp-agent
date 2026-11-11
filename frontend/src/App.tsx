import React, { useState, useEffect, useRef } from 'react';
import { Header } from './components/Header';
import { RepoSelector } from './components/RepoSelector';
import { InvestigationStages } from './components/InvestigationStages';
import { ExecutionTrace } from './components/ExecutionTrace';
import { ToolLogViewer } from './components/ToolLogViewer';
import { PatchApprovalCard } from './components/PatchApprovalCard';
import { VerificationResultsCard } from './components/VerificationResultsCard';
import { EngineeringReportView } from './components/EngineeringReportView';
import { ArchitectureModal } from './components/ArchitectureModal';
import { SettingsModal } from './components/SettingsModal';
import type {
  Session,
  Stage,
  ExecutionEvent,
  ToolCall,
  Patch,
  TestRun,
  Report,
  SystemHealth,
} from './types';

export const App: React.FC = () => {
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [stages, setStages] = useState<Stage[]>([]);
  const [events, setEvents] = useState<ExecutionEvent[]>([]);
  const [toolCalls, setToolCalls] = useState<ToolCall[]>([]);
  const [currentPatch, setCurrentPatch] = useState<Patch | null>(null);
  const [testRuns, setTestRuns] = useState<TestRun[]>([]);
  const [report, setReport] = useState<Report | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Configuration State
  const [backendUrl, setBackendUrl] = useState<string>(() => {
    const saved = localStorage.getItem('devpilot_backend_url');
    if (saved && saved.trim()) return saved.trim();
    return (import.meta.env.VITE_API_BASE_URL as string) || 'https://devpilot-backend-production-69a81a4f.up.railway.app';
  });
  const [providerMode, setProviderMode] = useState<'live' | 'demo'>('demo');
  const [apiKey, setApiKey] = useState<string>('');
  const [backendConnected, setBackendConnected] = useState<boolean | null>(null);

  // UI State
  const [isRunning, setIsRunning] = useState<boolean>(false);
  const [isProcessingApproval, setIsProcessingApproval] = useState<boolean>(false);
  const [isResetting, setIsResetting] = useState<boolean>(false);
  const [showArchModal, setShowArchModal] = useState<boolean>(false);
  const [showSettingsModal, setShowSettingsModal] = useState<boolean>(false);
  const [rightTab, setRightTab] = useState<'trace' | 'tools' | 'tests' | 'report'>('trace');

  const eventSourceRef = useRef<EventSource | null>(null);
  const pollTimerRef = useRef<number | null>(null);

  const getApiUrl = (path: string): string => {
    const base = backendUrl.trim().replace(/\/+$/, '');
    return base ? `${base}${path}` : path;
  };

  // Fetch health on mount and when backendUrl changes
  useEffect(() => {
    fetchHealth();
    return () => {
      if (pollTimerRef.current) clearInterval(pollTimerRef.current);
      if (eventSourceRef.current) eventSourceRef.current.close();
    };
  }, [backendUrl]);

  const fetchHealth = async () => {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 3500);

      const res = await fetch(getApiUrl('/api/health'), {
        signal: controller.signal,
      });
      clearTimeout(timeoutId);

      if (res.ok) {
        const data = await res.json();
        setHealth(data);
        setBackendConnected(true);
        if (data.provider_mode === 'live' || data.provider_mode === 'demo') {
          setProviderMode(data.provider_mode);
        }
      } else {
        setBackendConnected(false);
      }
    } catch {
      setBackendConnected(false);
    }
  };

  const handleResetRepo = async () => {
    setIsResetting(true);
    setErrorMessage(null);
    try {
      if (backendConnected) {
        const res = await fetch(getApiUrl('/api/demo/reset'), { method: 'POST' });
        if (res.ok) {
          alert('Sample repository restored to baseline state with intentional bug.');
        }
      } else {
        // Reset simulated state
        setStages([]);
        setEvents([]);
        setToolCalls([]);
        setCurrentPatch(null);
        setTestRuns([]);
        setReport(null);
        setSession(null);
        alert('Sandbox state reset to baseline.');
      }
    } catch (e: any) {
      console.error('Error resetting repo', e);
    } finally {
      setIsResetting(false);
    }
  };

  // Standalone Client-side Simulation for Offline / Preview Mode
  const runStandaloneSimulation = async (task: string) => {
    const simSessionId = `session_sim_${Date.now().toString(36).slice(-6)}`;
    const now = () => new Date().toTimeString().slice(0, 8);

    setSession({
      id: simSessionId,
      repository_path: 'sample_repo',
      task_description: task,
      status: 'INVESTIGATING',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    });

    const addEvent = (
      category: ExecutionEvent['category'],
      title: string,
      detail: string,
      data?: any,
      status: ExecutionEvent['status'] = 'info'
    ) => {
      setEvents((prev) => [
        ...prev,
        {
          id: `evt_${Date.now()}_${Math.random().toString(36).substring(7)}`,
          session_id: simSessionId,
          category,
          title,
          detail,
          data,
          status,
          timestamp: now(),
        },
      ]);
    };

    const updateStage = (
      stage_id: number,
      name: string,
      status: Stage['status'],
      explanation: string,
      evidence: string = '',
      duration_seconds?: number
    ) => {
      setStages((prev) => {
        const existing = prev.filter((s) => s.stage_id !== stage_id);
        return [
          ...existing,
          {
            id: `${simSessionId}_stage_${stage_id}`,
            session_id: simSessionId,
            stage_id,
            name,
            status,
            explanation,
            evidence,
            duration_seconds,
          },
        ].sort((a, b) => a.stage_id - b.stage_id);
      });
    };

    // Stage 1: Initializing
    updateStage(1, 'Initializing agent and provider', 'running', 'Validating agent configuration and runtime environment...');
    addEvent('AGENT', 'Agent Initialized', `Mode: Demo (Simulated Replay) | Target: sample_auth_service`);
    await new Promise((r) => setTimeout(r, 450));
    updateStage(1, 'Initializing agent and provider', 'completed', 'Agent initialized in Demo Mode', 'Deterministic Replay Provider active', 0.45);

    // Stage 2: Connecting to MCP server
    updateStage(2, 'Connecting to the MCP server', 'running', 'Connecting to Model Context Protocol stdio subprocess...');
    addEvent('MCP', 'Connecting to MCP Server', 'Spawning stdio session with MCP 2.x protocol');
    await new Promise((r) => setTimeout(r, 400));
    updateStage(2, 'Connecting to the MCP server', 'completed', 'MCP stdio session established', 'Protocol: MCP 2.x stdio (stdio PID simulated)', 0.4);
    addEvent('MCP', 'MCP Server Connected', 'Transport: stdio | Protocol: MCP 2.x', null, 'success');

    // Stage 3: Discovering available tools
    updateStage(3, 'Discovering available tools', 'running', 'Querying MCP server for available tools via session.list_tools()...');
    addEvent('MCP', 'Discovering MCP Tools', 'Querying available tool schemas');
    await new Promise((r) => setTimeout(r, 400));
    const tools = [
      'inspect_repository', 'list_files', 'read_file', 'search_code',
      'run_tests', 'get_git_status', 'get_git_diff', 'propose_patch'
    ];
    updateStage(3, 'Discovering available tools', 'completed', 'Tools discovered', `Discovered 8 tools: ${tools.join(', ')}`, 0.4);
    addEvent('MCP', 'Tools Discovered', '8 MCP tools ready for orchestration', tools, 'success');

    // Stage 4: Running baseline tests
    updateStage(4, 'Running baseline tests', 'running', "Executing 'pytest -v --tb=short' via MCP tool run_tests...");
    addEvent('TOOL', 'MCP Tool Invocation: run_tests', 'Parameters: {"command": "pytest -v --tb=short"}');
    await new Promise((r) => setTimeout(r, 650));
    const baselineResult = {
      command: 'pytest -v --tb=short',
      exit_code: 1,
      passed: 2,
      failed: 1,
      skipped: 0,
      total: 3,
      duration_seconds: 0.65,
      output: 'FAILED tests/test_auth.py::test_valid_token_verification - TokenExpiredError: Token has expired',
      failures: [{ test_id: 'tests/test_auth.py::test_valid_token_verification', message: 'TokenExpiredError: Token has expired' }],
    };
    setToolCalls((prev) => [
      ...prev,
      {
        id: `call_run_tests_${Date.now()}`,
        session_id: simSessionId,
        tool_name: 'run_tests',
        arguments: { command: 'pytest -v --tb=short' },
        result: baselineResult,
        status: 'SUCCESS',
        duration_ms: 650,
        created_at: new Date().toISOString(),
      },
    ]);
    setTestRuns([
      {
        id: `run_baseline_${Date.now()}`,
        session_id: simSessionId,
        phase: 'BASELINE',
        command: 'pytest -v --tb=short',
        exit_code: 1,
        passed_count: 2,
        failed_count: 1,
        skipped_count: 0,
        total_count: 3,
        duration_seconds: 0.65,
        raw_output: baselineResult.output,
        test_cases: baselineResult.failures,
        created_at: new Date().toISOString(),
      },
    ]);
    updateStage(4, 'Running baseline tests', 'completed', 'Baseline test suite captured', 'Exit code 1 | 1 failed, 2 passed. Failing: test_valid_token_verification', 0.65);
    addEvent('TEST', 'Baseline Test Execution', '1 failed / 2 passed (Exit code 1)', baselineResult.failures, 'warning');

    // Stage 5: Inspecting repository files
    updateStage(5, 'Inspecting repository files and failing tests', 'running', 'Searching codebase for TokenExpiredError and reading auth_service/auth.py...');
    addEvent('TOOL', 'MCP Tool Invocation: search_code', 'query: "TokenExpiredError" in *.py');
    await new Promise((r) => setTimeout(r, 500));
    addEvent('TOOL', 'MCP Tool Invocation: read_file', 'file_path: "auth_service/auth.py", lines: 70-105');
    await new Promise((r) => setTimeout(r, 450));
    setToolCalls((prev) => [
      ...prev,
      {
        id: `call_search_${Date.now()}`,
        session_id: simSessionId,
        tool_name: 'search_code',
        arguments: { query: 'TokenExpiredError', file_pattern: '*.py' },
        result: { matches: [{ file: 'auth_service/auth.py', line: 89 }] },
        status: 'SUCCESS',
        duration_ms: 25,
        created_at: new Date().toISOString(),
      },
      {
        id: `call_read_${Date.now()}`,
        session_id: simSessionId,
        tool_name: 'read_file',
        arguments: { file_path: 'auth_service/auth.py', start_line: 70, end_line: 105 },
        result: {
          file_path: 'auth_service/auth.py',
          content: '88:     if payload.get("exp", 0) > current_time:\n89:         raise TokenExpiredError("Token has expired")',
        },
        status: 'SUCCESS',
        duration_ms: 20,
        created_at: new Date().toISOString(),
      },
    ]);
    updateStage(5, 'Inspecting repository files and failing tests', 'completed', 'Code inspected', 'Inspected auth_service/auth.py around token expiration logic', 0.95);

    // Stage 6: Identifying root cause
    updateStage(6, 'Identifying the root cause', 'running', 'Analyzing token expiration check logic...');
    await new Promise((r) => setTimeout(r, 400));
    updateStage(6, 'Identifying the root cause', 'completed', 'Root cause identified', 'Inverted comparison operator: payload.get("exp", 0) > current_time in auth.py:88', 0.4);
    addEvent('AGENT', 'Root Cause Diagnosed', 'Inverted comparison operator: Fresh unexpired tokens were rejected as expired.', null, 'success');

    // Stage 7: Preparing proposed patch
    updateStage(7, 'Preparing a proposed patch', 'running', 'Synthesizing minimal diff patch and generating cryptographic token...');
    addEvent('TOOL', 'MCP Tool Invocation: propose_patch', 'Target: auth_service/auth.py');
    await new Promise((r) => setTimeout(r, 500));
    const diff =
      '--- a/auth_service/auth.py\n' +
      '+++ b/auth_service/auth.py\n' +
      '@@ -88,3 +88,3 @@\n' +
      '-    if payload.get("exp", 0) > current_time:\n' +
      '+    if payload.get("exp", 0) < current_time:\n';
    const rationale =
      'The token verification routine had an inverted comparison operator in the expiration check. ' +
      'It checked payload["exp"] > current_time, causing freshly issued, valid tokens with future expiration timestamps to be rejected immediately with TokenExpiredError. Inverting the condition to < correctly permits unexpired tokens and rejects expired ones.';
    const patchId = `patch_${Date.now().toString(36)}`;
    const approvalToken = 'e7f8a9b1c2d3e4f5061728394a5b6c7d8e9f0123456789abcdef0123456789ab';

    const patchObj: Patch = {
      id: patchId,
      session_id: simSessionId,
      target_file: 'auth_service/auth.py',
      diff,
      rationale,
      status: 'PENDING_APPROVAL',
      approval_token: approvalToken,
      created_at: new Date().toISOString(),
    };
    setCurrentPatch(patchObj);
    setToolCalls((prev) => [
      ...prev,
      {
        id: `call_propose_${Date.now()}`,
        session_id: simSessionId,
        tool_name: 'propose_patch',
        arguments: { target_file: 'auth_service/auth.py', diff, rationale },
        result: { patch_id: patchId, approval_token: approvalToken, target_file: 'auth_service/auth.py' },
        status: 'SUCCESS',
        duration_ms: 35,
        created_at: new Date().toISOString(),
      },
    ]);
    updateStage(7, 'Preparing a proposed patch', 'completed', 'Patch proposed with cryptographic approval token', `Patch ID: ${patchId} | Token: ${approvalToken.slice(0, 12)}...`, 0.5);
    addEvent('TOOL', 'Patch Proposed via MCP', `Target: auth_service/auth.py | Token: ${approvalToken.slice(0, 12)}...`, { patch_id: patchId }, 'success');

    // Stage 8: Waiting for human approval
    updateStage(8, 'Waiting for human approval', 'running', 'Halting automated execution. Backend authorization requires explicit human approval before any file writes.', `Awaiting user authorization for Patch ID: ${patchId}`);
    addEvent('APPROVAL', 'Execution Paused: Awaiting Human Authorization', 'Human-in-the-loop governance: write operations blocked until token is confirmed.', { patch_id: patchId }, 'warning');

    setSession((prev) => (prev ? { ...prev, status: 'AWAITING_APPROVAL' } : null));
    setIsRunning(false);
  };

  const handleRunOfflineDemo = async (task: string) => {
    setIsRunning(true);
    setErrorMessage(null);
    setToolCalls([]);
    setCurrentPatch(null);
    setTestRuns([]);
    setReport(null);
    setStages([]);
    setEvents([]);
    await runStandaloneSimulation(task);
  };

  const startInvestigation = async (task: string) => {
    setIsRunning(true);
    setErrorMessage(null);
    setToolCalls([]);
    setCurrentPatch(null);
    setTestRuns([]);
    setReport(null);
    setStages([]);
    setEvents([]);

    // Check if Live Gemini mode was selected but no API key is provided
    if (providerMode === 'live' && !apiKey.trim() && !health?.gemini_api_key_configured) {
      setErrorMessage(
        'Live Gemini Mode requires a valid GEMINI_API_KEY. Please provide an API key in Settings or switch to Demo Mode.'
      );
      setIsRunning(false);
      setShowSettingsModal(true);
      return;
    }

    // If backend is offline, refuse silent fallback and require explicit user action
    if (!backendConnected) {
      setIsRunning(false);
      setErrorMessage(
        `Backend Connection Error: Unable to reach DevPilot API backend at ${backendUrl || window.location.origin}. ` +
        `Live investigation requires an active backend server to launch MCP subprocesses. ` +
        `Please check your backend status, open Settings to set the Backend URL, or click 'Run Offline Demo'.`
      );
      return;
    }

    // Clean up prior subscriptions
    if (eventSourceRef.current) eventSourceRef.current.close();
    if (pollTimerRef.current) clearInterval(pollTimerRef.current);

    try {
      // 1. Create Session
      const createRes = await fetch(getApiUrl('/api/sessions'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          task,
          provider_mode: providerMode,
          api_key: apiKey || undefined,
        }),
      });

      if (!createRes.ok) {
        const errData = await createRes.json();
        throw new Error(errData.detail || 'Failed to create session');
      }

      const createData = await createRes.json();
      const newSessionId = createData.session_id;
      setSession(createData.session);

      // Helper to refresh session state
      const pollSession = async () => {
        try {
          const detailRes = await fetch(getApiUrl(`/api/sessions/${newSessionId}`));
          if (detailRes.ok) {
            const data = await detailRes.json();
            if (data.session) setSession(data.session);
            if (data.stages && data.stages.length > 0) setStages(data.stages);
            if (data.events && data.events.length > 0) setEvents(data.events);
            if (data.tool_calls) setToolCalls(data.tool_calls);
            if (data.patches && data.patches.length > 0) setCurrentPatch(data.patches[0]);
            if (data.test_runs) setTestRuns(data.test_runs);
            if (data.report) setReport(data.report);

            if (data.session?.status === 'AWAITING_APPROVAL' || data.session?.status === 'COMPLETED' || data.session?.status === 'FAILED') {
              setIsRunning(false);
            }
          }
        } catch (e) {
          console.warn('Poll error', e);
        }
      };

      // 2. Connect SSE stream
      try {
        const sse = new EventSource(getApiUrl(`/api/sessions/${newSessionId}/stream`));
        eventSourceRef.current = sse;

        sse.addEventListener('snapshot', (e: MessageEvent) => {
          try {
            const snap = JSON.parse(e.data);
            if (snap.session) setSession(snap.session);
            if (snap.stages) setStages(snap.stages);
            if (snap.events) setEvents(snap.events);
            if (snap.tool_calls) setToolCalls(snap.tool_calls);
            if (snap.patches && snap.patches.length > 0) setCurrentPatch(snap.patches[0]);
            if (snap.test_runs) setTestRuns(snap.test_runs);
            if (snap.report) setReport(snap.report);
          } catch (err) {
            console.error('Error parsing snapshot', err);
          }
        });

        sse.addEventListener('stage_update', (e: MessageEvent) => {
          const data = JSON.parse(e.data);
          setStages((prev) => {
            const existing = prev.filter((s) => s.stage_id !== data.stage_id);
            return [...existing, data].sort((a, b) => a.stage_id - b.stage_id);
          });
        });

        sse.addEventListener('execution_event', (e: MessageEvent) => {
          const data = JSON.parse(e.data);
          setEvents((prev) => [...prev, data]);
        });

        sse.addEventListener('tool_result', (e: MessageEvent) => {
          const data = JSON.parse(e.data);
          const newCall: ToolCall = {
            id: `call_${Date.now()}_${Math.random().toString(36).substring(7)}`,
            session_id: newSessionId,
            tool_name: data.tool,
            arguments: data.arguments || {},
            result: data.result,
            status: 'SUCCESS',
            duration_ms: data.result?.duration_seconds ? Math.round(data.result.duration_seconds * 1000) : 15,
            created_at: new Date().toISOString(),
          };
          setToolCalls((prev) => [...prev, newCall]);
        });

        sse.addEventListener('patch_proposed', (e: MessageEvent) => {
          const data = JSON.parse(e.data);
          const newPatch: Patch = {
            id: data.patch_id,
            session_id: newSessionId,
            target_file: data.target_file,
            diff: data.diff,
            rationale: data.rationale,
            status: 'PENDING_APPROVAL',
            approval_token: data.approval_token,
            created_at: new Date().toISOString(),
          };
          setCurrentPatch(newPatch);
          setSession((prev) => (prev ? { ...prev, status: 'AWAITING_APPROVAL' } : null));
          setIsRunning(false);
        });

        sse.addEventListener('investigation_failed', (e: MessageEvent) => {
          const data = JSON.parse(e.data);
          setErrorMessage(`Investigation Failed: ${data.error}`);
          setIsRunning(false);
        });

        sse.onerror = () => {
          // Fall back to polling if SSE has network hiccup
          console.warn('SSE encountered error, relying on active polling');
        };
      } catch (err) {
        console.warn('SSE initialization failed, will poll', err);
      }

      // Start fallback polling every 1000ms
      pollTimerRef.current = window.setInterval(pollSession, 1000);

      // 3. Trigger Investigation
      const startRes = await fetch(getApiUrl(`/api/sessions/${newSessionId}/investigate`), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          task,
          provider_mode: providerMode,
          api_key: apiKey || undefined,
        }),
      });

      if (!startRes.ok) {
        const err = await startRes.json();
        throw new Error(err.detail || 'Failed to trigger investigation');
      }
    } catch (e: any) {
      console.error('Error starting investigation', e);
      setErrorMessage(e.message || 'Investigation failed to initialize');
      setIsRunning(false);
    }
  };

  const handleApprovePatch = async (patchId: string, token: string) => {
    if (!session) return;
    setIsProcessingApproval(true);
    setErrorMessage(null);

    // Standalone Simulation mode handler
    if (!backendConnected) {
      await new Promise((r) => setTimeout(r, 600));
      // Stage 8 completed
      setStages((prev) => {
        const list = prev.map((s) =>
          s.stage_id === 8 ? { ...s, status: 'completed' as const, evidence: `Token authorized: ${token.slice(0, 12)}...` } : s
        );
        return list;
      });
      setEvents((prev) => [
        ...prev,
        {
          id: `evt_${Date.now()}`,
          session_id: session.id,
          category: 'APPROVAL',
          title: 'Patch Approved by User',
          detail: `Token authorized: ${token.slice(0, 12)}...`,
          status: 'success',
          timestamp: new Date().toTimeString().slice(0, 8),
        },
      ]);

      // Stage 9: Apply patch
      setStages((prev) => [
        ...prev.filter((s) => s.stage_id !== 9),
        {
          id: `${session.id}_stage_9`,
          session_id: session.id,
          stage_id: 9,
          name: 'Applying the approved patch',
          status: 'completed',
          explanation: 'Applying authorized patch diff to repository...',
          evidence: 'Applied diff to auth_service/auth.py successfully',
          duration_seconds: 0.15,
        },
      ]);
      setEvents((prev) => [
        ...prev,
        {
          id: `evt_${Date.now()}`,
          session_id: session.id,
          category: 'TOOL',
          title: 'Patch Applied to Repository',
          detail: 'File auth_service/auth.py modified on disk',
          status: 'success',
          timestamp: new Date().toTimeString().slice(0, 8),
        },
      ]);
      setCurrentPatch((prev) => (prev ? { ...prev, status: 'APPLIED' } : null));

      // Stage 10: Run verification test suite
      await new Promise((r) => setTimeout(r, 700));
      const verifyRun: TestRun = {
        id: `run_verify_${Date.now()}`,
        session_id: session.id,
        phase: 'VERIFICATION',
        command: 'pytest -v',
        exit_code: 0,
        passed_count: 3,
        failed_count: 0,
        skipped_count: 0,
        total_count: 3,
        duration_seconds: 0.68,
        raw_output: '3 passed in 0.68s',
        test_cases: [],
        created_at: new Date().toISOString(),
      };
      setTestRuns((prev) => [...prev, verifyRun]);

      setStages((prev) => [
        ...prev.filter((s) => s.stage_id !== 10),
        {
          id: `${session.id}_stage_10`,
          session_id: session.id,
          stage_id: 10,
          name: 'Running post-patch verification',
          status: 'completed',
          explanation: 'Executing full verification test suite to check for fixes and regressions...',
          evidence: 'Verification Exit Code: 0. Passed: 3/3. Fixed: 1, Regressions: 0.',
          duration_seconds: 0.68,
        },
      ]);
      setEvents((prev) => [
        ...prev,
        {
          id: `evt_${Date.now()}`,
          session_id: session.id,
          category: 'VERIFICATION',
          title: 'Verification Outcome: VERIFIED',
          detail: '3 passed, 0 failed. Clean success with 0 regressions.',
          status: 'success',
          timestamp: new Date().toTimeString().slice(0, 8),
        },
        {
          id: `evt_rep_${Date.now()}`,
          session_id: session.id,
          category: 'AGENT',
          title: 'Final Engineering Report Synthesized',
          detail: 'Persisted in audit database',
          status: 'success',
          timestamp: new Date().toTimeString().slice(0, 8),
        },
      ]);

      const reportMarkdown = `# DevPilot Verification & Engineering Audit Report

## 1. Executive Summary
Autonomous investigation of authentication service test failure. Root cause was diagnosed as an inverted comparison operator in the token expiration logic. Patch proposed, authorized by human reviewer, applied, and verified against full test suite.

- **Repository Root**: \`sample_repo\`
- **Branch**: \`master\`
- **Test Suite Count**: 3 tests evaluated

## 2. Baseline Test Failure
- **Command**: \`pytest -v --tb=short\`
- **Exit Code**: \`1\`
- **Symptom**: \`test_valid_token_verification\` failed with \`TokenExpiredError: Token has expired\` for valid tokens.

## 3. Root Cause Analysis
- **Target File**: \`auth_service/auth.py\`
- **Category**: Logic Inversion / Comparison Operator Flaw
- **Explanation**: In \`auth_service/auth.py\` at line 88, the token expiration check was implemented as:
  \`if payload.get('exp', 0) > current_time:\`
  Because unexpired tokens legitimately have \`exp > current_time\`, this condition incorrectly evaluated to True for all valid tokens, raising \`TokenExpiredError\` immediately upon issuance.

## 4. Proposed & Applied Patch
- **Patch Status**: APPROVED_AND_APPLIED
- **Unified Diff**:
\`\`\`diff
--- a/auth_service/auth.py
+++ b/auth_service/auth.py
@@ -88,3 +88,3 @@
-    if payload.get("exp", 0) > current_time:
+    if payload.get("exp", 0) < current_time:
\`\`\`

## 5. Post-Patch Verification
- **Verification Status**: **VERIFIED**
- **Exit Code**: \`0\`
- **Passed**: 3
- **Failed**: 0
- **Regressions**: 0
- **Evidence**:
  - Baseline Failures Resolved: \`tests/test_auth.py::test_valid_token_verification\`
  - Clean Success across entire test suite.
`;

      setReport({
        id: `report_${Date.now().toString(36)}`,
        session_id: session.id,
        summary: 'Inverted comparison operator in token expiration check fixed and verified.',
        root_cause: 'Inverted expiration comparison operator in verify_token()',
        patch_summary: 'Changed > to < in auth_service/auth.py',
        verification_status: 'VERIFIED',
        full_markdown: reportMarkdown,
        created_at: new Date().toISOString(),
      });
      setSession((prev) => (prev ? { ...prev, status: 'COMPLETED' } : null));
      setIsProcessingApproval(false);
      setRightTab('report');
      return;
    }

    // Live Backend approval
    try {
      const res = await fetch(getApiUrl(`/api/sessions/${session.id}/patches/${patchId}/approve`), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ approval_token: token }),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Approval Authorization Failed');
      }

      const data = await res.json();
      setCurrentPatch((prev) => (prev ? { ...prev, status: 'APPLIED' } : null));
      setSession((prev) => (prev ? { ...prev, status: data.status } : null));

      // Refresh full details
      const detailRes = await fetch(getApiUrl(`/api/sessions/${session.id}`));
      if (detailRes.ok) {
        const details = await detailRes.json();
        if (details.test_runs) setTestRuns(details.test_runs);
        if (details.report) setReport(details.report);
        if (details.stages) setStages(details.stages);
        if (details.events) setEvents(details.events);
      }
      setRightTab('report');
    } catch (e: any) {
      console.error('Error approving patch', e);
      setErrorMessage(e.message || 'Failed to authorize and apply patch');
    } finally {
      setIsProcessingApproval(false);
      setIsRunning(false);
    }
  };

  const handleRejectPatch = async (patchId: string, reason: string) => {
    if (!session) return;
    try {
      if (backendConnected) {
        await fetch(getApiUrl(`/api/sessions/${session.id}/patches/${patchId}/reject`), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ reason }),
        });
      }
      setCurrentPatch((prev) => (prev ? { ...prev, status: 'REJECTED', decision_reason: reason } : null));
      setSession((prev) => (prev ? { ...prev, status: 'REJECTED' } : null));
      setStages((prev) =>
        prev.map((s) =>
          s.stage_id === 8
            ? {
                ...s,
                status: 'failed' as const,
                explanation: `Patch rejected by user: ${reason}`,
                evidence: 'Write permission denied by reviewer. No files modified.',
              }
            : s
        )
      );
      setEvents((prev) => [
        ...prev,
        {
          id: `evt_rej_${Date.now()}`,
          session_id: session.id,
          category: 'APPROVAL',
          title: 'Patch Rejected by Reviewer',
          detail: `Reason: ${reason}`,
          status: 'warning',
          timestamp: new Date().toTimeString().slice(0, 8),
        },
      ]);
    } catch (e: any) {
      console.error('Error rejecting patch', e);
    }
  };

  return (
    <div className="min-h-screen bg-[#fbfaf8] text-[#18181b] flex flex-col font-sans antialiased">
      {/* Navigation Header */}
      <Header
        health={health}
        providerMode={providerMode}
        onResetRepo={handleResetRepo}
        onOpenArchitecture={() => setShowArchModal(true)}
        onOpenSettings={() => setShowSettingsModal(true)}
        isResetting={isResetting}
      />

      {/* Offline / Preview Mode Notice Banner */}
      {backendConnected === false && (
        <div className="bg-rose-50 border-b border-rose-200 px-4 py-3 text-xs text-rose-950">
          <div className="max-w-7xl mx-auto flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex items-start sm:items-center gap-2.5">
              <span className="text-base leading-none">⚠️</span>
              <div>
                <strong className="font-semibold text-rose-900">Backend Server Offline</strong>
                <span className="text-rose-800 ml-1.5">
                  Cannot communicate with DevPilot API ({backendUrl || 'Local / Relative'}). Live MCP tool calls require a running backend server.
                </span>
              </div>
            </div>
            <div className="flex items-center gap-2 self-end sm:self-auto shrink-0">
              <button
                type="button"
                onClick={() => handleRunOfflineDemo(
                  'Investigate why the authentication tests are failing, identify the root cause, propose a fix, and verify the solution. Do not modify anything without approval.'
                )}
                className="px-2.5 py-1 text-xs font-semibold rounded bg-amber-100 hover:bg-amber-200 text-amber-900 border border-amber-300 transition-colors"
              >
                Run Offline Demo Simulation
              </button>
              <button
                type="button"
                onClick={() => setShowSettingsModal(true)}
                className="px-2.5 py-1 text-xs font-semibold rounded bg-white hover:bg-stone-100 text-zinc-800 border border-stone-300 transition-colors"
              >
                Configure Endpoint
              </button>
              <button
                type="button"
                onClick={fetchHealth}
                className="text-xs text-rose-700 hover:text-rose-900 underline font-medium ml-1"
              >
                Retry
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Error Alert Banner */}
      {errorMessage && (
        <div className="bg-rose-50 border-b border-rose-200 px-4 py-2.5 text-xs text-rose-900">
          <div className="max-w-7xl mx-auto flex items-center justify-between">
            <span className="font-medium">{errorMessage}</span>
            <button
              onClick={() => setErrorMessage(null)}
              className="text-rose-600 hover:text-rose-800 font-bold ml-4"
            >
              ×
            </button>
          </div>
        </div>
      )}

      {/* Main Content Layout */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Left Column: Repo Selector, 10-Stage Pipeline, Patch Approval */}
          <div className="lg:col-span-5 space-y-6">
            <RepoSelector
              onStartInvestigation={startInvestigation}
              onRunOfflineDemo={handleRunOfflineDemo}
              isRunning={isRunning}
              activeSessionId={session?.id}
              providerMode={providerMode}
              backendConnected={backendConnected}
              onOpenSettings={() => setShowSettingsModal(true)}
            />

            {/* 10-Stage Investigation Pipeline */}
            <InvestigationStages stages={stages} />

            {/* Human Governance Approval Card */}
            {currentPatch && (
              <PatchApprovalCard
                patch={currentPatch}
                onApprove={handleApprovePatch}
                onReject={handleRejectPatch}
                isProcessing={isProcessingApproval}
              />
            )}
          </div>

          {/* Right Column: Tabbed Evidence Center (Execution Trace, Tools, Test Results, Final Report) */}
          <div className="lg:col-span-7 space-y-6">
            {/* Tab Navigation */}
            <div className="bg-white rounded-xl border border-stone-200 p-1 shadow-xs flex items-center justify-between">
              <div className="flex items-center gap-1 text-xs">
                <button
                  type="button"
                  onClick={() => setRightTab('trace')}
                  className={`px-3.5 py-1.5 rounded-lg font-semibold transition-all ${
                    rightTab === 'trace'
                      ? 'bg-orange-600 text-white shadow-xs'
                      : 'text-zinc-600 hover:text-zinc-900 hover:bg-stone-100'
                  }`}
                >
                  Live Trace ({events.length})
                </button>

                <button
                  type="button"
                  onClick={() => setRightTab('tools')}
                  className={`px-3.5 py-1.5 rounded-lg font-semibold transition-all ${
                    rightTab === 'tools'
                      ? 'bg-orange-600 text-white shadow-xs'
                      : 'text-zinc-600 hover:text-zinc-900 hover:bg-stone-100'
                  }`}
                >
                  MCP Tools ({toolCalls.length})
                </button>

                <button
                  type="button"
                  onClick={() => setRightTab('tests')}
                  className={`px-3.5 py-1.5 rounded-lg font-semibold transition-all ${
                    rightTab === 'tests'
                      ? 'bg-orange-600 text-white shadow-xs'
                      : 'text-zinc-600 hover:text-zinc-900 hover:bg-stone-100'
                  }`}
                >
                  Test Results ({testRuns.length})
                </button>

                <button
                  type="button"
                  onClick={() => setRightTab('report')}
                  className={`px-3.5 py-1.5 rounded-lg font-semibold transition-all ${
                    rightTab === 'report'
                      ? 'bg-orange-600 text-white shadow-xs'
                      : 'text-zinc-600 hover:text-zinc-900 hover:bg-stone-100'
                  }`}
                >
                  Engineering Report {report && '✓'}
                </button>
              </div>

              {session && (
                <div className="pr-3 text-[11px] font-mono text-zinc-500 hidden sm:block">
                  Status: <strong className="text-zinc-800">{session.status}</strong>
                </div>
              )}
            </div>

            {/* Active Tab View */}
            {rightTab === 'trace' && <ExecutionTrace events={events} />}

            {rightTab === 'tools' && <ToolLogViewer toolCalls={toolCalls} />}

            {rightTab === 'tests' && <VerificationResultsCard testRuns={testRuns} />}

            {rightTab === 'report' && (
              <EngineeringReportView report={report} />
            )}
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-stone-200 bg-white py-4 mt-auto">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between text-xs text-zinc-500 gap-2">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-zinc-800">DevPilot</span>
            <span>—</span>
            <span>AI Software Engineering Agent</span>
          </div>
          <div>
            <span>Model Context Protocol 2.x • Google GenAI • SQLite Audit Trace</span>
          </div>
        </div>
      </footer>

      {/* Architecture & Specs Modal */}
      <ArchitectureModal
        isOpen={showArchModal}
        onClose={() => setShowArchModal(false)}
      />

      {/* Settings Modal */}
      <SettingsModal
        isOpen={showSettingsModal}
        onClose={() => setShowSettingsModal(false)}
        backendUrl={backendUrl}
        setBackendUrl={(url) => {
          setBackendUrl(url);
          localStorage.setItem('devpilot_backend_url', url);
        }}
        providerMode={providerMode}
        setProviderMode={setProviderMode}
        apiKey={apiKey}
        setApiKey={setApiKey}
        health={health}
        onRefreshHealth={fetchHealth}
      />
    </div>
  );
};
export default App;
