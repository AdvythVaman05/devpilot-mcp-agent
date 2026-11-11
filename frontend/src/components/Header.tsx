import React from 'react';
import { Terminal, RefreshCw, BookOpen, ExternalLink, Settings as SettingsIcon } from 'lucide-react';
import type { SystemHealth } from '../types';

interface HeaderProps {
  health: SystemHealth | null;
  providerMode: 'live' | 'demo';
  onResetRepo: () => void;
  onOpenArchitecture: () => void;
  onOpenSettings: () => void;
  isResetting: boolean;
}

export const Header: React.FC<HeaderProps> = ({
  health,
  providerMode,
  onResetRepo,
  onOpenArchitecture,
  onOpenSettings,
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
              <span className="px-2 py-0.5 text-xs font-semibold rounded-full bg-orange-100 text-orange-700 border border-orange-200">
                MCP Agent
              </span>
            </div>
            <p className="text-xs text-[#52525b] hidden sm:block">
              AI-Native Software Engineering & Protocol Architecture
            </p>
          </div>
        </div>

        {/* Status Pills and Actions */}
        <div className="flex items-center space-x-2.5">
          {/* Provider Mode Pill */}
          <div
            onClick={onOpenSettings}
            className={`hidden sm:flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium rounded-md border cursor-pointer transition-colors ${
              providerMode === 'live'
                ? 'bg-emerald-50 text-emerald-800 border-emerald-200 hover:bg-emerald-100'
                : 'bg-amber-50 text-amber-800 border-amber-200 hover:bg-amber-100'
            }`}
            title="Click to configure provider mode and credentials"
          >
            <span
              className={`h-2 w-2 rounded-full ${
                providerMode === 'live' ? 'bg-emerald-500' : 'bg-amber-500'
              }`}
            ></span>
            <span>{providerMode === 'live' ? 'Live Gemini' : 'Demo Mode'}</span>
          </div>

          {/* Backend Status Pill */}
          <div
            onClick={onOpenSettings}
            className={`hidden sm:flex items-center space-x-1.5 text-xs px-2.5 py-1.5 rounded-md border cursor-pointer transition-colors ${
              health
                ? 'bg-emerald-50/70 border-emerald-200 text-emerald-800 hover:bg-emerald-100'
                : 'bg-rose-50 border-rose-200 text-rose-700 hover:bg-rose-100'
            }`}
            title={health ? 'Backend Connected: MCP 2.x Server Active' : 'Backend Unreachable: Click to configure URL in Settings'}
          >
            <span className={`h-2 w-2 rounded-full ${health ? 'bg-emerald-500' : 'bg-rose-500 animate-pulse'}`}></span>
            <span>{health ? 'Backend: Online' : 'Backend: Offline'}</span>
          </div>

          {/* Settings Button */}
          <button
            onClick={onOpenSettings}
            className="flex items-center space-x-1.5 px-3 py-1.5 text-xs font-medium text-[#18181b] bg-[#f4f2ee] hover:bg-[#e9e6df] rounded-md border border-[#e4e2dd] transition-colors"
          >
            <SettingsIcon className="h-3.5 w-3.5 text-[#52525b]" />
            <span>Settings</span>
          </button>

          {/* Architecture Modal */}
          <button
            onClick={onOpenArchitecture}
            className="hidden md:flex items-center space-x-1.5 px-3 py-1.5 text-xs font-medium text-[#18181b] bg-[#f4f2ee] hover:bg-[#e9e6df] rounded-md border border-[#e4e2dd] transition-colors"
          >
            <BookOpen className="h-3.5 w-3.5 text-[#52525b]" />
            <span>Specs</span>
          </button>

          {/* Reset Sandbox */}
          <button
            onClick={onResetRepo}
            disabled={isResetting}
            title="Reset sample repository back to initial failing state"
            className="flex items-center space-x-1.5 px-3 py-1.5 text-xs font-medium text-[#52525b] hover:text-[#18181b] bg-[#ffffff] hover:bg-[#f4f2ee] rounded-md border border-[#e4e2dd] transition-colors"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${isResetting ? 'animate-spin text-[#ea580c]' : ''}`} />
            <span className="hidden sm:inline">Reset</span>
          </button>

          {/* GitHub Repo Link */}
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
