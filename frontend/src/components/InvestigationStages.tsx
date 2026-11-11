import React, { useState } from 'react';
import type { Stage } from '../types';

interface InvestigationStagesProps {
  stages: Stage[];
}

const DEFAULT_STAGES = [
  { stage_id: 1, name: 'Initializing agent and provider', defaultExpl: 'Validating agent configuration and LLM provider credentials...' },
  { stage_id: 2, name: 'Connecting to the MCP server', defaultExpl: 'Spawning and connecting to Model Context Protocol stdio subprocess...' },
  { stage_id: 3, name: 'Discovering available tools', defaultExpl: 'Querying MCP server for tool definitions and JSON schemas...' },
  { stage_id: 4, name: 'Running baseline tests', defaultExpl: 'Executing repository test suite to observe and capture failures...' },
  { stage_id: 5, name: 'Inspecting repository files and failing tests', defaultExpl: 'Locating failing assertions and reading relevant source files...' },
  { stage_id: 6, name: 'Identifying the root cause', defaultExpl: 'Analyzing failure mechanism and formulating corrective logic...' },
  { stage_id: 7, name: 'Preparing a proposed patch', defaultExpl: 'Synthesizing minimal diff patch and generating cryptographic token...' },
  { stage_id: 8, name: 'Waiting for human approval', defaultExpl: 'Halting automated execution to wait for explicit user authorization...' },
  { stage_id: 9, name: 'Applying the approved patch', defaultExpl: 'Applying cryptographic authorized patch to target source file...' },
  { stage_id: 10, name: 'Running post-patch verification', defaultExpl: 'Executing verification test suite and evaluating regression diff...' },
];

export const InvestigationStages: React.FC<InvestigationStagesProps> = ({ stages }) => {
  const [expandedStage, setExpandedStage] = useState<number | null>(null);

  // Merge default definitions with active stages
  const stageList = DEFAULT_STAGES.map((def) => {
    const live = stages.find((s) => s.stage_id === def.stage_id);
    return {
      stage_id: def.stage_id,
      name: live?.name || def.name,
      status: live?.status || 'pending',
      explanation: live?.explanation || def.defaultExpl,
      evidence: live?.evidence || '',
      duration_seconds: live?.duration_seconds,
      started_at: live?.started_at,
      completed_at: live?.completed_at,
    };
  });

  const toggleExpand = (id: number) => {
    setExpandedStage((prev) => (prev === id ? null : id));
  };

  return (
    <div className="bg-white rounded-xl border border-stone-200 shadow-xs overflow-hidden">
      {/* Header */}
      <div className="px-5 py-3.5 border-b border-stone-100 bg-stone-50/70 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-2.5 h-2.5 rounded-full bg-orange-600"></div>
          <h2 className="text-sm font-semibold text-zinc-900 tracking-tight">
            10-Stage Investigation Pipeline
          </h2>
        </div>
        <div className="text-xs font-mono text-zinc-600 bg-stone-100 px-2 py-0.5 rounded border border-stone-200">
          {stageList.filter((s) => s.status === 'completed').length}/10 Completed
        </div>
      </div>

      {/* Stages List */}
      <div className="divide-y divide-stone-100">
        {stageList.map((st) => {
          const isExpanded = expandedStage === st.stage_id;
          const hasEvidence = Boolean(st.evidence && st.evidence.trim());

          return (
            <div
              key={st.stage_id}
              className={`transition-colors text-xs ${
                st.status === 'running'
                  ? 'bg-orange-50/40'
                  : st.status === 'failed'
                  ? 'bg-rose-50/30'
                  : 'hover:bg-stone-50/60'
              }`}
            >
              <div
                onClick={() => hasEvidence && toggleExpand(st.stage_id)}
                className={`p-3.5 flex items-start gap-3 ${hasEvidence ? 'cursor-pointer' : ''}`}
              >
                {/* Stage Number / Status Icon */}
                <div className="pt-0.5 shrink-0">
                  {st.status === 'completed' && (
                    <div className="w-5 h-5 rounded-full bg-emerald-100 text-emerald-700 flex items-center justify-center font-bold text-xs border border-emerald-300">
                      ✓
                    </div>
                  )}
                  {st.status === 'running' && (
                    <div className="w-5 h-5 rounded-full bg-orange-100 text-orange-600 flex items-center justify-center text-xs font-bold border border-orange-400 animate-pulse">
                      ●
                    </div>
                  )}
                  {st.status === 'failed' && (
                    <div className="w-5 h-5 rounded-full bg-rose-100 text-rose-700 flex items-center justify-center font-bold text-xs border border-rose-300">
                      ✕
                    </div>
                  )}
                  {st.status === 'pending' && (
                    <div className="w-5 h-5 rounded-full bg-stone-100 text-zinc-600 flex items-center justify-center font-mono text-[11px] border border-stone-300">
                      {st.stage_id}
                    </div>
                  )}
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-2 mb-1">
                    <span
                      className={`font-semibold text-xs truncate ${
                        st.status === 'completed'
                          ? 'text-zinc-900'
                          : st.status === 'running'
                          ? 'text-orange-900 font-bold'
                          : st.status === 'failed'
                          ? 'text-rose-900 font-bold'
                          : 'text-zinc-600'
                      }`}
                    >
                      Stage {st.stage_id}: {st.name}
                    </span>

                    <div className="flex items-center gap-1.5 shrink-0">
                      {st.duration_seconds !== undefined && st.duration_seconds !== null && (
                        <span className="text-[10px] font-mono text-zinc-600 bg-stone-100 px-1.5 py-0.5 rounded border border-stone-200">
                          {st.duration_seconds}s
                        </span>
                      )}

                      <span
                        className={`text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded border ${
                          st.status === 'completed'
                            ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
                            : st.status === 'running'
                            ? 'bg-orange-100 text-orange-800 border-orange-300'
                            : st.status === 'failed'
                            ? 'bg-rose-50 text-rose-800 border-rose-200'
                            : 'bg-stone-100 text-zinc-600 border-stone-200'
                        }`}
                      >
                        {st.status}
                      </span>

                      {hasEvidence && (
                        <span className="text-[10px] text-zinc-600">
                          {isExpanded ? '▲' : '▼'}
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Explanation */}
                  <p
                    className={`text-[11px] leading-relaxed ${
                      st.status === 'running'
                        ? 'text-orange-950 font-medium'
                        : st.status === 'failed'
                        ? 'text-rose-950 font-medium'
                        : 'text-zinc-700'
                    }`}
                  >
                    {st.explanation}
                  </p>

                  {/* Collapsed Evidence Summary Teaser */}
                  {!isExpanded && hasEvidence && (
                    <div className="mt-1.5 flex items-center gap-1.5 text-[11px] text-zinc-800 font-mono truncate bg-stone-50 px-2 py-1 rounded border border-stone-200">
                      <span className="font-sans font-semibold text-zinc-800 shrink-0">Evidence:</span>
                      <span className="truncate">{st.evidence}</span>
                    </div>
                  )}
                </div>
              </div>

              {/* Expanded Output / Evidence Drawer */}
              {isExpanded && hasEvidence && (
                <div className="px-11 pb-3 pt-1">
                  <div className="p-2.5 rounded-lg bg-stone-900 text-stone-100 font-mono text-[11px] leading-relaxed overflow-x-auto border border-stone-800">
                    <div className="text-[10px] font-sans font-semibold text-orange-400 uppercase tracking-wider mb-1">
                      Stage Output & Verified Evidence
                    </div>
                    <pre className="whitespace-pre-wrap break-all font-mono">
                      {st.evidence}
                    </pre>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
