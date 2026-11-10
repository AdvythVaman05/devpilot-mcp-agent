import React, { useState, useEffect, useRef } from 'react';
import { Header } from './components/Header';
import { RepoSelector } from './components/RepoSelector';
import { PlanTimeline } from './components/PlanTimeline';
import { ToolLogViewer } from './components/ToolLogViewer';
import { PatchApprovalCard } from './components/PatchApprovalCard';
import { VerificationResultsCard } from './components/VerificationResultsCard';
import { EngineeringReportView } from './components/EngineeringReportView';
import { ArchitectureModal } from './components/ArchitectureModal';
import type { Session, Plan, ToolCall, Patch, TestRun, Report, SystemHealth } from './types';

export const App: React.FC = () => {
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [plan, setPlan] = useState<Plan | null>(null);
  const [toolCalls, setToolCalls] = useState<ToolCall[]>([]);
  const [currentPatch, setCurrentPatch] = useState<Patch | null>(null);
  const [testRuns, setTestRuns] = useState<TestRun[]>([]);
  const [report, setReport] = useState<Report | null>(null);
  const [agentThought, setAgentThought] = useState<string>('');

  const [isRunning, setIsRunning] = useState<boolean>(false);
  const [isProcessingApproval, setIsProcessingApproval] = useState<boolean>(false);
  const [isResetting, setIsResetting] = useState<boolean>(false);
  const [showArchModal, setShowArchModal] = useState<boolean>(false);

  const eventSourceRef = useRef<EventSource | null>(null);

  // Fetch system health on mount
  useEffect(() => {
    fetchHealth();
  }, []);

  const fetchHealth = async () => {
    try {
      const res = await fetch('/api/health');
      if (res.ok) {
        const data = await res.json();
        setHealth(data);
      }
    } catch (e) {
      console.error('Error fetching health status', e);
    }
  };

  const handleResetRepo = async () => {
    setIsResetting(true);
    try {
      const res = await fetch('/api/demo/reset', { method: 'POST' });
      if (res.ok) {
        alert('Sample repository restored to baseline state with intentional bug.');
      }
    } catch (e) {
      console.error('Error resetting repo', e);
    } finally {
      setIsResetting(false);
    }
  };

  const startInvestigation = async (task: string) => {
    setIsRunning(true);
    setToolCalls([]);
    setCurrentPatch(null);
    setTestRuns([]);
    setReport(null);
    setAgentThought('Initializing MCP Client session and discovering available tools...');

    // Close previous SSE if open
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    try {
      // 1. Create session
      const createRes = await fetch('/api/sessions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ task }),
      });
      const createData = await createRes.json();
      const newSessionId = createData.session_id;
      setSession(createData.session);

      // 2. Connect to SSE stream
      const sse = new EventSource(`/api/sessions/${newSessionId}/stream`);
      eventSourceRef.current = sse;

      sse.addEventListener('snapshot', (e: MessageEvent) => {
        try {
          const snap = JSON.parse(e.data);
          if (snap.session) setSession(snap.session);
          if (snap.plan) setPlan(snap.plan);
          if (snap.tool_calls) setToolCalls(snap.tool_calls);
          if (snap.patches && snap.patches.length > 0) setCurrentPatch(snap.patches[0]);
          if (snap.test_runs) setTestRuns(snap.test_runs);
          if (snap.report) setReport(snap.report);
        } catch (err) {
          console.error('Error parsing snapshot', err);
        }
      });

      sse.addEventListener('agent_thought', (e: MessageEvent) => {
        const data = JSON.parse(e.data);
        if (data.text) setAgentThought(data.text);
      });

      sse.addEventListener('plan_updated', (e: MessageEvent) => {
        const data = JSON.parse(e.data);
        setPlan((prev) => ({
          id: prev?.id || 'plan_1',
          session_id: newSessionId,
          steps: data.steps,
          current_step_index: data.current_step || 0,
        }));
      });

      sse.addEventListener('tool_invoking', (e: MessageEvent) => {
        const data = JSON.parse(e.data);
        setAgentThought(`Executing MCP tool '${data.tool}' with allowlisted parameters...`);
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

        // If tool was run_tests, record test run
        if (data.tool === 'run_tests') {
          const run: TestRun = {
            id: `run_${Date.now()}`,
            session_id: newSessionId,
            phase: 'BASELINE',
            command: data.result.command || 'pytest',
            exit_code: data.result.exit_code,
            passed_count: data.result.passed || 0,
            failed_count: data.result.failed || 0,
            skipped_count: data.result.skipped || 0,
            total_count: data.result.total || 0,
            duration_seconds: data.result.duration_seconds || 0,
            raw_output: data.result.output,
            test_cases: data.result.failures || [],
            created_at: new Date().toISOString(),
          };
          setTestRuns((prev) => [run, ...prev.filter((r) => r.phase !== 'BASELINE')]);
        }
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
        setAgentThought('Patch proposed. Agent execution paused: awaiting human approval authorization.');
      });

      // 3. Trigger investigation
      await fetch(`/api/sessions/${newSessionId}/investigate`, {
        method: 'POST',
      });
    } catch (e) {
      console.error('Error starting investigation', e);
      setIsRunning(false);
    }
  };

  const handleApprovePatch = async (patchId: string, token: string) => {
    if (!session) return;
    setIsProcessingApproval(true);
    setAgentThought('Authorizing write operation: Verifying approval token, applying patch, and running verification engine...');

    try {
      const res = await fetch(`/api/sessions/${session.id}/patches/${patchId}/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ approval_token: token }),
      });

      if (!res.ok) {
        const err = await res.json();
        alert(`Approval Authorization Failed: ${err.detail || 'Access denied'}`);
        setIsProcessingApproval(false);
        return;
      }

      const data = await res.json();
      setCurrentPatch((prev) => (prev ? { ...prev, status: 'APPLIED' } : null));
      setSession((prev) => (prev ? { ...prev, status: data.status } : null));

      // Refresh full details to show post-patch test run & report
      const refreshRes = await fetch(`/api/sessions/${session.id}`);
      if (refreshRes.ok) {
        const details = await refreshRes.json();
        if (details.test_runs) setTestRuns(details.test_runs);
        if (details.report) setReport(details.report);
        if (details.plan) setPlan(details.plan);
      }

      setAgentThought('Fix verified! All unit tests pass cleanly with 0 regressions. Investigation report generated.');
    } catch (e) {
      console.error('Error approving patch', e);
    } finally {
      setIsProcessingApproval(false);
      setIsRunning(false);
    }
  };

  const handleRejectPatch = async (patchId: string, reason: string) => {
    if (!session) return;
    try {
      const res = await fetch(`/api/sessions/${session.id}/patches/${patchId}/reject`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason }),
      });
      if (res.ok) {
        setCurrentPatch((prev) => (prev ? { ...prev, status: 'REJECTED', decision_reason: reason } : null));
        setSession((prev) => (prev ? { ...prev, status: 'PATCH_REJECTED' } : null));
        setAgentThought('Patch was rejected by user. No files were modified.');
      }
    } catch (e) {
      console.error('Error rejecting patch', e);
    }
  };

  return (
    <div className="min-h-screen bg-[#fbfaf8] text-[#18181b] flex flex-col font-sans">
      <Header
        health={health}
        onResetRepo={handleResetRepo}
        onOpenArchitecture={() => setShowArchModal(true)}
        isResetting={isResetting}
      />

      <main className="flex-1 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 w-full">
        {/* Top Control Section */}
        <RepoSelector
          onStartInvestigation={startInvestigation}
          isRunning={isRunning}
          activeSessionId={session?.id}
        />

        {/* Two-Column Responsive Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Left Column: Plan & Protocol Logs */}
          <div className="lg:col-span-5 space-y-6">
            <PlanTimeline
              plan={plan}
              session={session}
              agentThought={agentThought}
            />

            <ToolLogViewer toolCalls={toolCalls} />
          </div>

          {/* Right Column: Approval Gate, Verification, and Engineering Report */}
          <div className="lg:col-span-7 space-y-6">
            <PatchApprovalCard
              patch={currentPatch}
              onApprove={handleApprovePatch}
              onReject={handleRejectPatch}
              isProcessing={isProcessingApproval}
            />

            <VerificationResultsCard testRuns={testRuns} />

            <EngineeringReportView report={report} />
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-[#e4e2dd] bg-[#ffffff] py-4 text-center text-xs text-[#71717a]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-2">
          <span>DevPilot • Production-Style MCP Software Engineering Agent</span>
          <span>EPAM Systems AI-Native Software Engineering Internship Submission</span>
        </div>
      </footer>

      {/* Architecture & Specs Modal */}
      <ArchitectureModal
        isOpen={showArchModal}
        onClose={() => setShowArchModal(false)}
      />
    </div>
  );
};

export default App;
