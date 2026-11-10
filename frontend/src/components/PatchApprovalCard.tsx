import React, { useState } from 'react';
import { ShieldAlert, CheckCircle2, XCircle, FileCode, KeyRound, AlertTriangle } from 'lucide-react';
import type { Patch } from '../types';

interface PatchApprovalCardProps {
  patch: Patch | null;
  onApprove: (patchId: string, token: string) => void;
  onReject: (patchId: string, reason: string) => void;
  isProcessing: boolean;
}

export const PatchApprovalCard: React.FC<PatchApprovalCardProps> = ({
  patch,
  onApprove,
  onReject,
  isProcessing,
}) => {
  const [rejectReason, setRejectReason] = useState('');
  const [showRejectModal, setShowRejectModal] = useState(false);

  if (!patch) return null;

  const isPending = patch.status === 'PENDING_APPROVAL';
  const isApplied = patch.status === 'APPLIED';
  const isRejected = patch.status === 'REJECTED';

  // Render unified diff with syntax styling
  const renderDiffLines = (diff: string) => {
    return diff.split('\n').map((line, idx) => {
      let lineClass = 'text-[#18181b]';
      let bgClass = 'bg-transparent';

      if (line.startsWith('---') || line.startsWith('+++') || line.startsWith('@@')) {
        lineClass = 'text-[#0284c7] font-bold';
        bgClass = 'bg-sky-50/50';
      } else if (line.startsWith('+')) {
        lineClass = 'text-emerald-700 font-medium';
        bgClass = 'bg-emerald-50';
      } else if (line.startsWith('-')) {
        lineClass = 'text-red-700 font-medium';
        bgClass = 'bg-red-50';
      }

      return (
        <div key={idx} className={`px-3 py-0.5 font-mono text-[11px] leading-5 ${lineClass} ${bgClass}`}>
          {line || ' '}
        </div>
      );
    });
  };

  return (
    <div className="bg-[#ffffff] rounded-xl border border-[#e4e2dd] p-5 shadow-xs mb-6">
      {/* Header Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-[#e4e2dd]">
        <div className="flex items-center space-x-2.5">
          <div
            className={`p-2 rounded-lg ${
              isPending
                ? 'bg-[#ffedd5] text-[#ea580c]'
                : isApplied
                ? 'bg-emerald-100 text-emerald-800'
                : 'bg-red-100 text-red-800'
            }`}
          >
            <ShieldAlert className="h-5 w-5" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h3 className="font-semibold text-sm text-[#18181b]">
                Human-in-the-Loop Governance Gate
              </h3>
              <span
                className={`text-xs px-2 py-0.5 rounded-full font-medium border ${
                  isPending
                    ? 'bg-amber-50 text-amber-800 border-amber-200 animate-pulse'
                    : isApplied
                    ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
                    : 'bg-red-50 text-red-800 border-red-200'
                }`}
              >
                {patch.status.replace('_', ' ')}
              </span>
            </div>
            <p className="text-xs text-[#52525b] mt-0.5">
              Backend authorization strictly requires human approval before filesystem modification.
            </p>
          </div>
        </div>

        {/* Patch ID & Token */}
        <div className="flex items-center space-x-2 text-xs bg-[#f4f2ee] px-2.5 py-1.5 rounded-md border border-[#e4e2dd]">
          <KeyRound className="h-3.5 w-3.5 text-[#71717a]" />
          <span className="font-mono text-[11px] text-[#52525b] truncate max-w-[140px]" title={patch.approval_token}>
            Token: {patch.approval_token.slice(0, 12)}...
          </span>
        </div>
      </div>

      {/* Target File & Technical Rationale */}
      <div className="mt-4 space-y-3">
        <div className="flex items-center space-x-2 text-xs text-[#18181b]">
          <FileCode className="h-4 w-4 text-[#ea580c]" />
          <span className="font-medium">Target Source File:</span>
          <span className="font-mono bg-[#f4f2ee] px-2 py-0.5 rounded text-[#ea580c] font-semibold border border-[#e4e2dd]">
            {patch.target_file}
          </span>
        </div>

        <div className="p-3 bg-[#faf8f5] rounded-lg border border-[#e4e2dd] text-xs">
          <span className="font-semibold text-[#18181b] block mb-1">Diagnostic Rationale:</span>
          <p className="text-[#52525b] leading-relaxed">{patch.rationale}</p>
        </div>

        {/* Proposed Unified Diff Viewer */}
        <div>
          <div className="flex items-center justify-between text-xs text-[#52525b] mb-1.5">
            <span className="font-medium">Proposed Unified Diff:</span>
            <span className="text-[11px] text-[#71717a]">Unified Diff Format</span>
          </div>
          <div className="rounded-lg border border-[#e4e2dd] overflow-hidden bg-[#faf8f5]">
            <div className="bg-[#f4f2ee] px-3 py-1.5 border-b border-[#e4e2dd] flex items-center justify-between text-[11px] text-[#71717a] font-mono">
              <span>{patch.target_file}</span>
              <span>Changes: Invert &gt; to &lt;</span>
            </div>
            <div className="py-1 max-h-60 overflow-y-auto">
              {renderDiffLines(patch.diff)}
            </div>
          </div>
        </div>

        {/* Human Action Controls */}
        {isPending && (
          <div className="pt-2 flex flex-col sm:flex-row items-center justify-end gap-2.5">
            <button
              onClick={() => setShowRejectModal(true)}
              disabled={isProcessing}
              className="w-full sm:w-auto px-4 py-2 text-xs font-medium text-red-700 bg-red-50 hover:bg-red-100 border border-red-200 rounded-lg flex items-center justify-center space-x-1.5 transition-colors"
            >
              <XCircle className="h-3.5 w-3.5" />
              <span>Reject Patch</span>
            </button>

            <button
              onClick={() => onApprove(patch.id, patch.approval_token)}
              disabled={isProcessing}
              className="w-full sm:w-auto px-5 py-2 text-xs font-semibold text-white bg-[#ea580c] hover:bg-[#c2410c] rounded-lg flex items-center justify-center space-x-2 shadow-xs transition-colors"
            >
              {isProcessing ? (
                <>
                  <span className="h-3.5 w-3.5 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
                  <span>Applying & Verifying...</span>
                </>
              ) : (
                <>
                  <CheckCircle2 className="h-3.5 w-3.5" />
                  <span>Authorize & Apply Fix</span>
                </>
              )}
            </button>
          </div>
        )}

        {isApplied && (
          <div className="p-3 bg-emerald-50 rounded-lg border border-emerald-200 text-xs text-emerald-800 flex items-center space-x-2">
            <CheckCircle2 className="h-4 w-4 text-emerald-600 shrink-0" />
            <span>
              Patch has been authorized and applied to source files. Verification test suite executed.
            </span>
          </div>
        )}

        {isRejected && (
          <div className="p-3 bg-red-50 rounded-lg border border-red-200 text-xs text-red-800 flex items-center space-x-2">
            <AlertTriangle className="h-4 w-4 text-red-600 shrink-0" />
            <span>
              Patch was rejected by user. Reason: {patch.decision_reason || 'Rejected'}. No files were modified.
            </span>
          </div>
        )}
      </div>

      {/* Reject Modal */}
      {showRejectModal && (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-xs flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl max-w-md w-full p-5 border border-[#e4e2dd] shadow-lg">
            <h4 className="font-semibold text-sm text-[#18181b] mb-2">Reject Proposed Patch</h4>
            <p className="text-xs text-[#52525b] mb-3">
              Explain why this proposed patch should not be applied. The agent will record your feedback.
            </p>
            <textarea
              rows={3}
              value={rejectReason}
              onChange={(e) => setRejectReason(e.target.value)}
              placeholder="e.g. Solution does not adhere to conventions or test criteria..."
              className="w-full text-xs p-2.5 border border-[#e4e2dd] rounded-lg mb-4 focus:ring-2 focus:ring-red-500 focus:outline-none"
            />
            <div className="flex justify-end space-x-2">
              <button
                onClick={() => setShowRejectModal(false)}
                className="px-3 py-1.5 text-xs text-[#52525b] hover:bg-zinc-100 rounded-lg"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  onReject(patch.id, rejectReason || 'Rejected by user');
                  setShowRejectModal(false);
                }}
                className="px-4 py-1.5 text-xs font-semibold text-white bg-red-600 hover:bg-red-700 rounded-lg"
              >
                Confirm Rejection
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
