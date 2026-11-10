import React from 'react';
import { Terminal, RefreshCw, BookOpen, ExternalLink } from 'lucide-react';
import type { SystemHealth } from '../types';

interface HeaderProps {
  health: SystemHealth | null;
  onResetRepo: () => void;
  onOpenArchitecture: () => void;
  isResetting: boolean;
}

export const Header: React.FC<HeaderProps> = ({
  health,
  onResetRepo,
  onOpenArchitecture,
  isResetting,
}) => {
  return (
    <header className="border-b border-[#e4e2dd] bg-[#ffffff] sticky top-0 z-30 shadow-xs">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Brand */}
        <div className="flex items-center space-x-3">
          <div className="h-9 w-9 rounded-lg bg-[#ea580c] flex items-center justify-center text-white shadow-xs">
            <Terminal className="h-5 w-5" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className="font-semibold text-lg tracking-tight text-[#18181b]">DevPilot</span>
              <span className="px-2 py-0.5 text-xs font-medium rounded-full bg-[#ffedd5] text-[#ea580c] border border-[#fed7aa]">
                MCP Agent
              </span>
            </div>
            <p className="text-xs text-[#52525b] hidden sm:block">
              AI-Native Software Engineering & Protocol Architecture
            </p>
          </div>
        </div>

        {/* Status Pills and Actions */}
        <div className="flex items-center space-x-3">
          {health && (
            <div className="hidden md:flex items-center space-x-2 text-xs bg-[#f4f2ee] px-2.5 py-1.5 rounded-md border border-[#e4e2dd]">
              <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse"></span>
              <span className="text-[#52525b]">{health.protocol}</span>
              <span className="text-[#a1a1aa]">•</span>
              <span className="font-medium text-[#18181b]">{health.active_provider}</span>
            </div>
          )}

          <button
            onClick={onOpenArchitecture}
            className="flex items-center space-x-1.5 px-3 py-1.5 text-xs font-medium text-[#18181b] bg-[#f4f2ee] hover:bg-[#e9e6df] rounded-md border border-[#e4e2dd] transition-colors"
          >
            <BookOpen className="h-3.5 w-3.5 text-[#52525b]" />
            <span>Architecture & Specs</span>
          </button>

          <button
            onClick={onResetRepo}
            disabled={isResetting}
            title="Reset sample repository back to initial failing state"
            className="flex items-center space-x-1.5 px-3 py-1.5 text-xs font-medium text-[#52525b] hover:text-[#18181b] bg-[#ffffff] hover:bg-[#f4f2ee] rounded-md border border-[#e4e2dd] transition-colors"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${isResetting ? 'animate-spin text-[#ea580c]' : ''}`} />
            <span className="hidden sm:inline">Reset Sandbox</span>
          </button>

          <a
            href="https://github.com/AdvythVaman05/devpilot-mcp-agent"
            target="_blank"
            rel="noreferrer"
            className="flex items-center space-x-1 px-3 py-1.5 text-xs font-medium text-white bg-[#18181b] hover:bg-[#27272a] rounded-md transition-colors"
          >
            <span>GitHub</span>
            <ExternalLink className="h-3 w-3" />
          </a>
        </div>
      </div>
    </header>
  );
};
