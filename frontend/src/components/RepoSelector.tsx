import React, { useState } from 'react';
import { GitBranch, Play, FolderGit2 } from 'lucide-react';

interface RepoSelectorProps {
  onStartInvestigation: (task: string) => void;
  isRunning: boolean;
  activeSessionId?: string;
}

export const RepoSelector: React.FC<RepoSelectorProps> = ({
  onStartInvestigation,
  isRunning,
  activeSessionId,
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
    <div className="bg-[#ffffff] rounded-xl border border-[#e4e2dd] p-5 shadow-xs mb-6">
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pb-4 border-b border-[#e4e2dd]">
        {/* Repo Card */}
        <div className="flex items-center space-x-3">
          <div className="p-2.5 bg-[#ffedd5] text-[#ea580c] rounded-lg border border-[#fed7aa]">
            <FolderGit2 className="h-5 w-5" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className="font-semibold text-sm text-[#18181b]">sample_auth_service</span>
              <span className="inline-flex items-center space-x-1 text-xs text-[#52525b] bg-[#f4f2ee] px-2 py-0.5 rounded border border-[#e4e2dd]">
                <GitBranch className="h-3 w-3" />
                <span>master</span>
              </span>
              <span className="text-xs bg-amber-50 text-amber-700 border border-amber-200 px-2 py-0.5 rounded font-medium">
                Intentional Bug: Active
              </span>
            </div>
            <p className="text-xs text-[#52525b] mt-0.5">
              Target: Python 3.14 • Pytest • HMAC-SHA256 JWT Microservice
            </p>
          </div>
        </div>

        {/* Preset Pills */}
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="text-xs font-medium text-[#71717a] mr-1">Presets:</span>
          {presets.map((p, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => setTaskInput(p.task)}
              disabled={isRunning}
              className="text-xs px-2.5 py-1 rounded bg-[#f4f2ee] hover:bg-[#e9e6df] text-[#18181b] border border-[#e4e2dd] transition-colors"
            >
              {p.title}
            </button>
          ))}
        </div>
      </div>

      {/* Task Form */}
      <form onSubmit={handleSubmit} className="mt-4">
        <label htmlFor="task" className="block text-xs font-medium text-[#52525b] mb-1.5 flex items-center justify-between">
          <span>Agent Task & Investigation Directive:</span>
          {activeSessionId && (
            <span className="text-[#a1a1aa] font-mono">Session: {activeSessionId}</span>
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
            className="flex-1 text-sm bg-[#faf8f5] text-[#18181b] border border-[#e4e2dd] rounded-lg px-3.5 py-2.5 focus:outline-none focus:ring-2 focus:ring-[#ea580c] focus:border-transparent transition-all"
          />
          <button
            type="submit"
            disabled={isRunning || !taskInput.trim()}
            className={`sm:w-44 px-4 py-2.5 rounded-lg text-sm font-medium text-white flex items-center justify-center space-x-2 transition-all ${
              isRunning
                ? 'bg-[#ea580c]/60 cursor-not-allowed'
                : 'bg-[#ea580c] hover:bg-[#c2410c] shadow-xs active:scale-[0.98]'
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
