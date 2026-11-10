import React from 'react';
import { X, CheckCircle, Terminal, Layers, Lock } from 'lucide-react';

interface ArchitectureModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const ArchitectureModal: React.FC<ArchitectureModalProps> = ({ isOpen, onClose }) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-xs flex items-center justify-center z-50 p-4 overflow-y-auto">
      <div className="bg-white rounded-2xl max-w-3xl w-full max-h-[90vh] overflow-y-auto border border-[#e4e2dd] shadow-2xl p-6 sm:p-8">
        <div className="flex items-center justify-between pb-4 border-b border-[#e4e2dd]">
          <div className="flex items-center space-x-2.5">
            <div className="h-8 w-8 rounded-lg bg-[#ea580c] flex items-center justify-center text-white">
              <Layers className="h-4 w-4" />
            </div>
            <div>
              <h2 className="text-base font-bold text-[#18181b]">DevPilot System Architecture & Protocol Specs</h2>
              <p className="text-xs text-[#52525b]">
                EPAM Systems AI-Native Software Engineering Internship Portfolio
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-md text-[#71717a] hover:text-[#18181b] hover:bg-[#f4f2ee]"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="mt-6 space-y-6 text-xs text-[#52525b]">
          {/* Section 1 */}
          <div>
            <h3 className="text-sm font-semibold text-[#18181b] flex items-center space-x-2 mb-2">
              <Terminal className="h-4 w-4 text-[#ea580c]" />
              <span>1. Genuine MCP Client/Server Architecture</span>
            </h3>
            <p className="leading-relaxed">
              DevPilot is not a simulated LLM function-calling wrapper. It implements a genuine Model Context Protocol (MCP) client and server over standard I/O (<code className="text-[#ea580c]">stdio</code> transport) using the official <code className="text-[#ea580c]">mcp</code> Python SDK. The custom repository MCP server exposes 8 strictly typed tools constrained to the repository sandbox.
            </p>
          </div>

          {/* Section 2 */}
          <div className="p-4 bg-[#faf8f5] rounded-xl border border-[#e4e2dd]">
            <h4 className="font-semibold text-xs text-[#18181b] uppercase tracking-wider mb-2">
              The 8 Sandboxed MCP Tools
            </h4>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-[11px] font-mono text-[#27272a]">
              <div className="p-2 bg-white rounded border border-[#e4e2dd]">1. inspect_repository</div>
              <div className="p-2 bg-white rounded border border-[#e4e2dd]">2. list_files</div>
              <div className="p-2 bg-white rounded border border-[#e4e2dd]">3. read_file</div>
              <div className="p-2 bg-white rounded border border-[#e4e2dd]">4. search_code</div>
              <div className="p-2 bg-white rounded border border-[#e4e2dd]">5. run_tests</div>
              <div className="p-2 bg-white rounded border border-[#e4e2dd]">6. get_git_status</div>
              <div className="p-2 bg-white rounded border border-[#e4e2dd]">7. get_git_diff</div>
              <div className="p-2 bg-white rounded border border-[#e4e2dd]">8. propose_patch</div>
            </div>
          </div>

          {/* Section 3 */}
          <div>
            <h3 className="text-sm font-semibold text-[#18181b] flex items-center space-x-2 mb-2">
              <Lock className="h-4 w-4 text-[#ea580c]" />
              <span>2. Backend-Enforced Human Approval (Governance)</span>
            </h3>
            <p className="leading-relaxed">
              Safety is enforced by cryptographic authorization logic, not by asking the LLM nicely. The <code className="text-[#ea580c]">propose_patch</code> tool stores diff proposals in SQLite with status <code className="text-[#ea580c]">PENDING_APPROVAL</code> and issues a SHA-256 token. Write operations to the filesystem fail with <code className="text-[#ea580c]">UnauthorizedWriteError</code> unless signed by the human operator.
            </p>
          </div>

          {/* Section 4 */}
          <div>
            <h3 className="text-sm font-semibold text-[#18181b] flex items-center space-x-2 mb-2">
              <CheckCircle className="h-4 w-4 text-[#ea580c]" />
              <span>3. Verification Engine Invariant</span>
            </h3>
            <p className="leading-relaxed">
              <strong>Core Invariant:</strong> A generated patch is not equivalent to a verified fix. DevPilot enforces regression test execution before and after every patch, comparing baseline failure IDs against post-patch outcomes to determine whether an issue is genuinely <code className="text-emerald-700">VERIFIED</code>.
            </p>
          </div>

          {/* Section 5 */}
          <div className="p-4 bg-[#ffedd5]/50 rounded-xl border border-[#fed7aa]">
            <h4 className="font-semibold text-xs text-[#ea580c] uppercase tracking-wider mb-2">
              Competency Alignment for EPAM AI-Native Engineering
            </h4>
            <ul className="list-disc pl-5 space-y-1 text-xs text-[#431407]">
              <li><strong>Agentic Software Development:</strong> Autonomous tool orchestration, planning, and multi-turn diagnostics.</li>
              <li><strong>Model Context Protocol:</strong> Dynamic tool schema conversion, Stdio transport, session management.</li>
              <li><strong>Production Governance:</strong> Cryptographic token enforcement and strict filesystem sandboxing.</li>
              <li><strong>Verification & QA:</strong> Automated pytest suite with 33 unit and integration tests passing.</li>
            </ul>
          </div>
        </div>

        <div className="mt-6 pt-4 border-t border-[#e4e2dd] flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 text-xs font-semibold text-white bg-[#18181b] hover:bg-[#27272a] rounded-lg"
          >
            Close Specifications
          </button>
        </div>
      </div>
    </div>
  );
};
