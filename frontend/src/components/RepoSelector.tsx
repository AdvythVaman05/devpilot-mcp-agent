import React, { useState } from 'react';
import { GitBranch, Play, FolderGit2, Info } from 'lucide-react';

interface RepoSelectorProps {
  onStartInvestigation: (task: string) => void;
  isRunning: boolean;
  activeSessionId?: string;
  providerMode: 'live' | 'demo';
  onOpenSettings: () => void;
}

export const RepoSelector: React.FC<RepoSelectorProps> = ({
  onStartInvestigation,
  isRunning,
  activeSessionId,
  providerMode,
  onOpenSettings,
}) => {
  const [taskInput, setTaskInput] = useState(
    'Investigate why the authentication tests are failing, identify the root cause, propose a fix, and verify the solution. Do not modify anything without approval.'
  );

  const presets = [
    {
      title: 'Fix Authentication Token Expiration Bug',
      desc: 'Investigate token verification failure and propose verified fix.',
      task: 'Investigate why the authentication tests are failing, identify the root cause, propose a fix, and verify the solution. Do not modify anything without approval.',
    },
    {
      title: 'Test Suite Baseline & Diagnostics',
      desc: 'Execute test suite and catalog failure tracebacks.',
      task: 'Run repository tests, inspect failure details in test_auth.py, and map the affected test assertions.',
    },
    {
      title: 'Repository Architecture & Security Audit',
      desc: 'Inspect codebase structure and verify role boundaries.',
      task: 'Inspect repository structure, list files, and analyze check_role_permission and cryptographic routines.',
    },
  ];

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!taskInput.trim() || isRunning) return;
    onStartInvestigation(taskInput);
  };

  return (
    <div className="bg-white rounded-xl border border-stone-200 p-5 shadow-xs mb-6">
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pb-4 border-b border-stone-200">
        {/* Repo Card */}
        <div className="flex items-center space-x-3">
          <div className="p-2.5 bg-orange-100 text-orange-600 rounded-lg border border-orange-200">
            <FolderGit2 className="h-5 w-5" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className="font-semibold text-sm text-zinc-900">sample_auth_service</span>
              <span className="inline-flex items-center space-x-1 text-xs text-zinc-600 bg-stone-100 px-2 py-0.5 rounded border border-stone-200">
                <GitBranch className="h-3 w-3" />
                <span>master</span>
              </span>
              <span className="text-xs bg-amber-50 text-amber-700 border border-amber-200 px-2 py-0.5 rounded font-medium">
                Intentional Bug: Active
              </span>
            </div>
            <p className="text-xs text-zinc-600 mt-0.5">
              Target: Python 3.11+ • Pytest • HMAC-SHA256 JWT Microservice
            </p>
          </div>
        </div>

        {/* Preset Pills */}
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="text-xs font-semibold text-zinc-700 mr-1">Presets:</span>
          {presets.map((p, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => setTaskInput(p.task)}
              disabled={isRunning}
              className="text-xs px-2.5 py-1 rounded bg-stone-100 hover:bg-stone-200 text-zinc-800 border border-stone-200 transition-colors"
            >
              {p.title}
            </button>
          ))}
        </div>
      </div>

      {/* Mode Notice Banner */}
      <div className="mt-3 px-3 py-2 rounded-lg bg-stone-50 border border-stone-200 flex items-center justify-between text-xs">
        <div className="flex items-center gap-2">
          <Info className="h-3.5 w-3.5 text-zinc-700 shrink-0" />
          <span className="text-zinc-700">
            Current Mode:{' '}
            <strong className="text-zinc-900">
              {providerMode === 'live' ? 'Live Google Gemini API' : 'Demo Mode (Deterministic Replay + Genuine MCP Tools)'}
            </strong>
          </span>
        </div>
        <button
          type="button"
          onClick={onOpenSettings}
          className="text-orange-600 hover:text-orange-700 font-medium hover:underline text-[11px]"
        >
          Change Mode in Settings →
        </button>
      </div>

      {/* Task Form */}
      <form onSubmit={handleSubmit} className="mt-3.5">
        <label htmlFor="task" className="block text-xs font-semibold text-zinc-700 mb-1.5 flex items-center justify-between">
          <span>Agent Task & Investigation Directive:</span>
          {activeSessionId && (
            <span className="text-zinc-600 font-mono text-[11px]">Session: {activeSessionId}</span>
          )}
        </label>
        <div className="flex flex-col sm:flex-row gap-2">
          <textarea
            id="task"
            rows={2}
            value={taskInput}
            onChange={(e) => setTaskInput(e.target.value)}
            disabled={isRunning}
            placeholder="Describe the software engineering task for DevPilot..."
            className="flex-1 text-sm bg-stone-50/60 text-zinc-900 border border-stone-300 rounded-lg px-3.5 py-2.5 focus:outline-hidden focus:ring-2 focus:ring-orange-500/20 focus:border-orange-500 transition-all font-sans"
          />
          <button
            type="submit"
            disabled={isRunning || !taskInput.trim()}
            className={`sm:w-44 px-4 py-2.5 rounded-lg text-sm font-semibold text-white flex items-center justify-center space-x-2 transition-all shadow-xs ${
              isRunning
                ? 'bg-orange-500/70 cursor-not-allowed'
                : 'bg-orange-600 hover:bg-orange-700 active:scale-[0.98]'
            }`}
          >
            {isRunning ? (
              <>
                <span className="h-4 w-4 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
                <span>Investigating...</span>
              </>
            ) : (
              <>
                <Play className="h-4 w-4 fill-white" />
                <span>Launch Agent</span>
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
};
