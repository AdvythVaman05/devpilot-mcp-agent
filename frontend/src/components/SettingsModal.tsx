import React, { useState } from 'react';
import type { SystemHealth } from '../types';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  backendUrl: string;
  setBackendUrl: (url: string) => void;
  providerMode: 'live' | 'demo';
  setProviderMode: (mode: 'live' | 'demo') => void;
  apiKey: string;
  setApiKey: (key: string) => void;
  health: SystemHealth | null;
  onRefreshHealth: () => Promise<void>;
}

export const SettingsModal: React.FC<SettingsModalProps> = ({
  isOpen,
  onClose,
  backendUrl,
  setBackendUrl,
  providerMode,
  setProviderMode,
  apiKey,
  setApiKey,
  health,
  onRefreshHealth,
}) => {
  const [localApiKey, setLocalApiKey] = useState(apiKey);
  const [localMode, setLocalMode] = useState<'live' | 'demo'>(providerMode);
  const [localBackendUrl, setLocalBackendUrl] = useState(backendUrl);
  const [showKey, setShowKey] = useState(false);

  const [testingGemini, setTestingGemini] = useState(false);
  const [geminiResult, setGeminiResult] = useState<{
    success: boolean;
    latency_ms?: number;
    error?: string;
    error_type?: string;
  } | null>(null);

  const [testingBackend, setTestingBackend] = useState(false);
  const [backendResult, setBackendResult] = useState<{
    success: boolean;
    statusText?: string;
  } | null>(null);

  if (!isOpen) return null;

  const handleTestGemini = async () => {
    setTestingGemini(true);
    setGeminiResult(null);
    try {
      const baseUrl = localBackendUrl.trim().replace(/\/+$/, '');
      const url = baseUrl ? `${baseUrl}/api/config/test-gemini` : '/api/config/test-gemini';
      const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ api_key: localApiKey }),
      });
      if (res.ok) {
        const data = await res.json();
        setGeminiResult(data);
      } else {
        setGeminiResult({
          success: false,
          error: `HTTP ${res.status}: ${res.statusText}`,
          error_type: 'NETWORK_ERROR',
        });
      }
    } catch (e: any) {
      setGeminiResult({
        success: false,
        error: e.message || 'Connection failed',
        error_type: 'NETWORK_ERROR',
      });
    } finally {
      setTestingGemini(false);
    }
  };

  const handleTestBackend = async () => {
    setTestingBackend(true);
    setBackendResult(null);
    try {
      const baseUrl = localBackendUrl.trim().replace(/\/+$/, '');
      const url = baseUrl ? `${baseUrl}/api/health` : '/api/health';
      const res = await fetch(url);
      if (res.ok) {
        setBackendResult({ success: true, statusText: 'Online & Ready (MCP stdio active)' });
        await onRefreshHealth();
      } else {
        setBackendResult({ success: false, statusText: `HTTP ${res.status}` });
      }
    } catch (e: any) {
      setBackendResult({ success: false, statusText: e.message || 'Unreachable' });
    } finally {
      setTestingBackend(false);
    }
  };

  const handleSave = async () => {
    setApiKey(localApiKey);
    setProviderMode(localMode);
    setBackendUrl(localBackendUrl);

    // If connected to backend, sync mode
    try {
      const baseUrl = localBackendUrl.trim().replace(/\/+$/, '');
      const url = baseUrl ? `${baseUrl}/api/config/set-mode` : '/api/config/set-mode';
      await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          provider_mode: localMode,
          api_key: localApiKey,
        }),
      });
      await onRefreshHealth();
    } catch {
      // Ignored if offline
    }

    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4">
      <div className="bg-white rounded-xl shadow-2xl border border-stone-200 max-w-lg w-full overflow-hidden flex flex-col max-h-[90vh]">
        {/* Modal Header */}
        <div className="px-6 py-4 border-b border-stone-100 flex items-center justify-between bg-stone-50/70">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-orange-100 flex items-center justify-center text-orange-600 font-bold text-sm">
              ⚙️
            </div>
            <div>
              <h2 className="text-base font-semibold text-zinc-900">Agent & API Configuration</h2>
              <p className="text-xs text-zinc-700">Configure provider mode, credentials, and backend connectivity</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-zinc-600 hover:text-zinc-800 text-lg font-semibold w-7 h-7 flex items-center justify-center rounded-md hover:bg-stone-200"
          >
            ×
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 space-y-6 overflow-y-auto">
          {/* Provider Mode Selection */}
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-800 mb-2">
              Execution Provider Mode
            </label>
            <div className="grid grid-cols-2 gap-3">
              <button
                type="button"
                onClick={() => setLocalMode('demo')}
                className={`p-3 rounded-lg border text-left transition-all ${
                  localMode === 'demo'
                    ? 'border-orange-500 bg-orange-50/50 ring-2 ring-orange-500/20'
                    : 'border-stone-200 hover:border-stone-300 bg-white'
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm font-semibold text-zinc-900">Demo Mode</span>
                  {localMode === 'demo' && (
                    <span className="w-2 h-2 rounded-full bg-orange-600"></span>
                  )}
                </div>
                <p className="text-xs text-zinc-700 leading-relaxed">
                  Deterministic simulation with genuine MCP tool execution. No API key required.
                </p>
              </button>

              <button
                type="button"
                onClick={() => setLocalMode('live')}
                className={`p-3 rounded-lg border text-left transition-all ${
                  localMode === 'live'
                    ? 'border-orange-500 bg-orange-50/50 ring-2 ring-orange-500/20'
                    : 'border-stone-200 hover:border-stone-300 bg-white'
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm font-semibold text-zinc-900">Live Gemini</span>
                  {localMode === 'live' && (
                    <span className="w-2 h-2 rounded-full bg-orange-600"></span>
                  )}
                </div>
                <p className="text-xs text-zinc-700 leading-relaxed">
                  Real Google GenAI Gemini function calling via official Python SDK.
                </p>
              </button>
            </div>
          </div>

          {/* Gemini API Key */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-800">
                Google Gemini API Key {localMode === 'live' ? <span className="text-red-500">*</span> : <span className="text-zinc-600 font-normal">(Optional for Demo)</span>}
              </label>
              <button
                type="button"
                onClick={() => setShowKey(!showKey)}
                className="text-xs text-orange-600 hover:text-orange-700 font-medium"
              >
                {showKey ? 'Hide Key' : 'Reveal Key'}
              </button>
            </div>
            <div className="flex gap-2">
              <input
                type={showKey ? 'text' : 'password'}
                value={localApiKey}
                onChange={(e) => {
                  setLocalApiKey(e.target.value);
                  setGeminiResult(null);
                }}
                placeholder="AIzaSy..."
                className="flex-1 px-3 py-2 text-sm font-mono border border-stone-300 rounded-lg focus:outline-hidden focus:ring-2 focus:ring-orange-500/20 focus:border-orange-500 bg-stone-50/50"
              />
              <button
                type="button"
                onClick={handleTestGemini}
                disabled={testingGemini || !localApiKey.trim()}
                className="px-3 py-2 bg-stone-100 hover:bg-stone-200 disabled:opacity-50 text-xs font-semibold text-zinc-700 rounded-lg border border-stone-200 transition-colors whitespace-nowrap"
              >
                {testingGemini ? 'Testing...' : 'Test Connection'}
              </button>
            </div>

            {/* Gemini Test Feedback */}
            {geminiResult && (
              <div
                className={`p-2.5 rounded-lg text-xs border ${
                  geminiResult.success
                    ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
                    : 'bg-rose-50 text-rose-800 border-rose-200'
                }`}
              >
                {geminiResult.success ? (
                  <div className="flex items-center justify-between">
                    <span className="font-medium">✓ Connection verified to Google Gemini</span>
                    <span className="font-mono text-[11px] bg-emerald-100 px-1.5 py-0.5 rounded">
                      {geminiResult.latency_ms} ms
                    </span>
                  </div>
                ) : (
                  <div>
                    <div className="font-semibold mb-0.5">Connection Failed ({geminiResult.error_type || 'Error'})</div>
                    <div className="text-[11px] font-mono break-all opacity-90">{geminiResult.error}</div>
                  </div>
                )}
              </div>
            )}

            <p className="text-[11px] text-zinc-600 leading-normal">
              🔒 <strong>Security Policy:</strong> Keys entered here reside in-memory for the active session. They are never written to disk, committed, or returned in API responses.
            </p>
          </div>

          {/* Backend Server URL */}
          <div className="space-y-2">
            <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-800">
              DevPilot Backend Endpoint
            </label>
            <div className="flex gap-2">
              <input
                type="text"
                value={localBackendUrl}
                onChange={(e) => {
                  setLocalBackendUrl(e.target.value);
                  setBackendResult(null);
                }}
                placeholder="http://localhost:8000 (empty for relative /api)"
                className="flex-1 px-3 py-2 text-sm font-mono border border-stone-300 rounded-lg focus:outline-hidden focus:ring-2 focus:ring-orange-500/20 focus:border-orange-500 bg-stone-50/50"
              />
              <button
                type="button"
                onClick={handleTestBackend}
                disabled={testingBackend}
                className="px-3 py-2 bg-stone-100 hover:bg-stone-200 disabled:opacity-50 text-xs font-semibold text-zinc-700 rounded-lg border border-stone-200 transition-colors whitespace-nowrap"
              >
                {testingBackend ? 'Testing...' : 'Test Backend'}
              </button>
            </div>

            {backendResult && (
              <div
                className={`p-2.5 rounded-lg text-xs border ${
                  backendResult.success
                    ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
                    : 'bg-amber-50 text-amber-800 border-amber-200'
                }`}
              >
                {backendResult.success ? (
                  <span>✓ Backend Connected: {backendResult.statusText}</span>
                ) : (
                  <span>⚠️ Backend Unreachable ({backendResult.statusText}). Operating in standalone browser simulation.</span>
                )}
              </div>
            )}

            <p className="text-[11px] text-zinc-600">
              When running locally, start the FastAPI server with <code className="bg-stone-100 px-1 py-0.5 rounded text-zinc-700">python -m devpilot.main</code>.
            </p>
          </div>

          {/* Connectivity Status Indicators */}
          <div className="pt-2 border-t border-stone-100 grid grid-cols-2 gap-2 text-xs">
            <div className="p-2.5 rounded-lg bg-stone-50 border border-stone-200">
              <div className="text-zinc-600 font-medium mb-1">LLM API Status</div>
              <div className="flex items-center gap-1.5 font-semibold text-zinc-800">
                <span
                  className={`w-2 h-2 rounded-full ${
                    localMode === 'live'
                      ? localApiKey.trim()
                        ? 'bg-emerald-500'
                        : 'bg-rose-500'
                      : 'bg-orange-500'
                  }`}
                ></span>
                {localMode === 'live'
                  ? localApiKey.trim()
                    ? 'Gemini Live'
                    : 'Missing Key'
                  : 'Demo (Simulated)'}
              </div>
            </div>

            <div className="p-2.5 rounded-lg bg-stone-50 border border-stone-200">
              <div className="text-zinc-600 font-medium mb-1">MCP Backend Status</div>
              <div className="flex items-center gap-1.5 font-semibold text-zinc-800">
                <span
                  className={`w-2 h-2 rounded-full ${
                    health?.status === 'ok' ? 'bg-emerald-500' : 'bg-amber-500'
                  }`}
                ></span>
                {health?.status === 'ok' ? 'MCP stdio Active' : 'Offline / Standalone'}
              </div>
            </div>
          </div>
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-3.5 border-t border-stone-100 bg-stone-50 flex items-center justify-end gap-3">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-xs font-semibold text-zinc-600 hover:text-zinc-800 rounded-lg hover:bg-stone-200 transition-colors"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleSave}
            className="px-4 py-2 text-xs font-semibold text-white bg-orange-600 hover:bg-orange-700 rounded-lg shadow-xs transition-colors"
          >
            Save & Apply
          </button>
        </div>
      </div>
    </div>
  );
};
