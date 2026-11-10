import React from 'react';
import { CheckCircle2, Circle, Clock, AlertTriangle } from 'lucide-react';
import type { Plan, Session } from '../types';

interface PlanTimelineProps {
  plan: Plan | null;
  session: Session | null;
  agentThought?: string;
}

export const PlanTimeline: React.FC<PlanTimelineProps> = ({
  plan,
  session,
  agentThought,
}) => {
  const steps = plan?.steps || [
    { id: '1', description: 'Execute baseline test suite to observe failure', status: 'PENDING' },
    { id: '2', description: 'Search code and inspect failing test and source files', status: 'PENDING' },
    { id: '3', description: 'Diagnose root cause and formulate solution', status: 'PENDING' },
    { id: '4', description: 'Formulate and propose code patch for review', status: 'PENDING' },
    { id: '5', description: 'Await human approval and authorization', status: 'PENDING' },
    { id: '6', description: 'Apply approved patch and execute verification engine', status: 'PENDING' },
  ];

  return (
    <div className="bg-[#ffffff] rounded-xl border border-[#e4e2dd] p-5 shadow-xs mb-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold text-sm text-[#18181b] flex items-center space-x-2">
          <Clock className="h-4 w-4 text-[#ea580c]" />
          <span>Investigation Plan & Execution Timeline</span>
        </h3>
        {session && (
          <span
            className={`text-xs px-2.5 py-0.5 rounded-full font-medium border ${
              session.status === 'COMPLETED'
                ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                : session.status === 'AWAITING_APPROVAL'
                ? 'bg-amber-50 text-amber-700 border-amber-200 animate-pulse'
                : session.status === 'INVESTIGATING' || session.status === 'VERIFYING'
                ? 'bg-orange-50 text-orange-700 border-orange-200'
                : 'bg-zinc-100 text-zinc-700 border-zinc-200'
            }`}
          >
            {session.status.replace('_', ' ')}
          </span>
        )}
      </div>

      {/* Steps List */}
      <div className="space-y-3 relative before:absolute before:left-3.5 before:top-3 before:bottom-3 before:w-0.5 before:bg-[#e4e2dd]">
        {steps.map((step, idx) => {
          const isDone = step.status === 'COMPLETED';
          const isCurrent = step.status === 'IN_PROGRESS';
          const isFailed = step.status === 'FAILED';

          return (
            <div key={step.id || idx} className="flex items-start space-x-3 relative z-10">
              <div className="mt-0.5">
                {isDone ? (
                  <CheckCircle2 className="h-7 w-7 text-emerald-600 bg-white rounded-full" />
                ) : isCurrent ? (
                  <div className="h-7 w-7 rounded-full bg-[#ffedd5] border-2 border-[#ea580c] flex items-center justify-center">
                    <span className="h-2.5 w-2.5 rounded-full bg-[#ea580c] animate-ping" />
                  </div>
                ) : isFailed ? (
                  <AlertTriangle className="h-7 w-7 text-red-600 bg-white rounded-full" />
                ) : (
                  <Circle className="h-7 w-7 text-[#d4d0c8] bg-white rounded-full" />
                )}
              </div>
              <div className="flex-1 pt-1">
                <p
                  className={`text-xs font-medium ${
                    isDone
                      ? 'text-[#18181b]'
                      : isCurrent
                      ? 'text-[#ea580c] font-semibold'
                      : 'text-[#71717a]'
                  }`}
                >
                  Step {idx + 1}: {step.description}
                </p>
              </div>
            </div>
          );
        })}
      </div>

      {/* Live Agent Thought / Reasoning Box */}
      {agentThought && (
        <div className="mt-4 p-3 bg-[#faf8f5] rounded-lg border border-[#e4e2dd] text-xs text-[#52525b]">
          <span className="font-semibold text-[#18181b] block mb-1">Agent Reasoning:</span>
          <p className="font-mono leading-relaxed">{agentThought}</p>
        </div>
      )}
    </div>
  );
};
