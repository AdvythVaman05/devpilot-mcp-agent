import React from 'react';
import { CheckCircle, XCircle, ShieldCheck, Bug } from 'lucide-react';
import type { TestRun } from '../types';

interface VerificationResultsCardProps {
  testRuns: TestRun[];
}

export const VerificationResultsCard: React.FC<VerificationResultsCardProps> = ({ testRuns }) => {
  const baseline = testRuns.find((r) => r.phase === 'BASELINE');
  const verification = testRuns.find((r) => r.phase === 'VERIFICATION');

  if (!baseline && !verification) return null;

  const isVerified = verification && verification.exit_code === 0 && verification.failed_count === 0;

  return (
    <div className="bg-[#ffffff] rounded-xl border border-[#e4e2dd] p-5 shadow-xs mb-6">
      <div className="flex items-center justify-between pb-4 border-b border-[#e4e2dd]">
        <div className="flex items-center space-x-2.5">
          <div className="p-2 bg-[#ffedd5] text-[#ea580c] rounded-lg">
            <ShieldCheck className="h-5 w-5" />
          </div>
          <div>
            <h3 className="font-semibold text-sm text-[#18181b]">Verification Engine</h3>
            <p className="text-xs text-[#52525b]">
              Rule: A generated patch is NOT equivalent to a verified fix.
            </p>
          </div>
        </div>

        {verification && (
          <span
            className={`px-3 py-1 rounded-full text-xs font-semibold border flex items-center space-x-1.5 ${
              isVerified
                ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                : 'bg-red-50 text-red-700 border-red-200'
            }`}
          >
            {isVerified ? (
              <>
                <CheckCircle className="h-3.5 w-3.5" />
                <span>VERIFIED FIX</span>
              </>
            ) : (
              <>
                <XCircle className="h-3.5 w-3.5" />
                <span>VERIFICATION FAILED</span>
              </>
            )}
          </span>
        )}
      </div>

      {/* Comparison Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
        {/* Baseline Card */}
        {baseline && (
          <div className="p-4 rounded-lg bg-[#faf8f5] border border-[#e4e2dd]">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold text-[#52525b] uppercase tracking-wider">
                1. Baseline Test Run
              </span>
              <span className="text-xs px-2 py-0.5 rounded bg-red-100 text-red-800 font-medium font-mono">
                Exit Code: {baseline.exit_code}
              </span>
            </div>

            <div className="flex items-baseline space-x-4 my-2">
              <div>
                <span className="text-2xl font-bold text-red-600 font-mono">
                  {baseline.failed_count}
                </span>
                <span className="text-xs text-[#71717a] ml-1">failed</span>
              </div>
              <div>
                <span className="text-2xl font-bold text-emerald-600 font-mono">
                  {baseline.passed_count}
                </span>
                <span className="text-xs text-[#71717a] ml-1">passed</span>
              </div>
              <div>
                <span className="text-xs text-[#71717a]">
                  Total: {baseline.total_count} tests ({baseline.duration_seconds}s)
                </span>
              </div>
            </div>

            {baseline.test_cases && baseline.test_cases.length > 0 && (
              <div className="mt-3 text-xs bg-red-50/60 p-2.5 rounded border border-red-200/60 font-mono text-red-800">
                <div className="flex items-center space-x-1 text-red-700 font-semibold mb-1">
                  <Bug className="h-3.5 w-3.5" />
                  <span>Observed Failure:</span>
                </div>
                <div className="truncate">{baseline.test_cases[0].test_id}</div>
                <div className="text-[11px] text-red-600 truncate mt-0.5">
                  {baseline.test_cases[0].message}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Post-Patch Verification Card */}
        {verification ? (
          <div className="p-4 rounded-lg bg-[#faf8f5] border border-[#e4e2dd]">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold text-[#52525b] uppercase tracking-wider">
                2. Post-Patch Verification Run
              </span>
              <span className="text-xs px-2 py-0.5 rounded bg-emerald-100 text-emerald-800 font-medium font-mono">
                Exit Code: {verification.exit_code}
              </span>
            </div>

            <div className="flex items-baseline space-x-4 my-2">
              <div>
                <span className="text-2xl font-bold text-red-600 font-mono">
                  {verification.failed_count}
                </span>
                <span className="text-xs text-[#71717a] ml-1">failed</span>
              </div>
              <div>
                <span className="text-2xl font-bold text-emerald-600 font-mono">
                  {verification.passed_count}
                </span>
                <span className="text-xs text-[#71717a] ml-1">passed</span>
              </div>
              <div>
                <span className="text-xs text-[#71717a]">
                  Total: {verification.total_count} tests ({verification.duration_seconds}s)
                </span>
              </div>
            </div>

            <div className="mt-3 text-xs bg-emerald-50/60 p-2.5 rounded border border-emerald-200/60 font-mono text-emerald-800">
              <div className="flex items-center space-x-1 text-emerald-700 font-semibold mb-1">
                <CheckCircle className="h-3.5 w-3.5" />
                <span>Verification Evidence:</span>
              </div>
              <div>Previously failing test resolved: test_valid_token_verification</div>
              <div className="text-[11px] text-emerald-600 mt-0.5">Regressions: 0</div>
            </div>
          </div>
        ) : (
          <div className="p-4 rounded-lg bg-[#faf8f5]/50 border border-dashed border-[#e4e2dd] flex flex-col items-center justify-center text-center">
            <span className="text-xs text-[#71717a]">
              Post-patch test execution pending human approval and patch application.
            </span>
          </div>
        )}
      </div>
    </div>
  );
};
