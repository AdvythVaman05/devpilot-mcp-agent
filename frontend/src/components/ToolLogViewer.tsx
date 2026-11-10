import React, { useState } from 'react';
import { Terminal, ChevronDown, ChevronRight, CheckCircle, AlertCircle, Clock } from 'lucide-react';
import type { ToolCall } from '../types';

interface ToolLogViewerProps {
  toolCalls: ToolCall[];
}

export const ToolLogViewer: React.FC<ToolLogViewerProps> = ({ toolCalls }) => {
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const toggleExpand = (id: string) => {
    setExpandedId(expandedId === id ? null : id);
  };

  return (
    <div className="bg-[#ffffff] rounded-xl border border-[#e4e2dd] p-5 shadow-xs mb-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold text-sm text-[#18181b] flex items-center space-x-2">
          <Terminal className="h-4 w-4 text-[#ea580c]" />
          <span>MCP Tool Invocations ({toolCalls.length})</span>
        </h3>
        <span className="text-xs text-[#71717a]">Model Context Protocol 2.x</span>
      </div>

      {toolCalls.length === 0 ? (
        <div className="py-8 text-center text-[#a1a1aa] text-xs">
          No MCP tools invoked yet. Launch an investigation to observe real protocol calls.
        </div>
      ) : (
        <div className="space-y-2">
          {toolCalls.map((call) => {
            const isExpanded = expandedId === call.id;
            const isSuccess = call.status === 'SUCCESS';

            return (
              <div
                key={call.id}
                className="border border-[#e4e2dd] rounded-lg overflow-hidden transition-all bg-[#faf8f5]"
              >
                <div
                  onClick={() => toggleExpand(call.id)}
                  className="flex items-center justify-between p-3 cursor-pointer hover:bg-[#f4f2ee] select-none"
                >
                  <div className="flex items-center space-x-2.5">
                    {isExpanded ? (
                      <ChevronDown className="h-4 w-4 text-[#71717a]" />
                    ) : (
                      <ChevronRight className="h-4 w-4 text-[#71717a]" />
                    )}
                    {isSuccess ? (
                      <CheckCircle className="h-4 w-4 text-emerald-600" />
                    ) : (
                      <AlertCircle className="h-4 w-4 text-red-500" />
                    )}
                    <span className="font-mono text-xs font-semibold text-[#18181b]">
                      {call.tool_name}
                    </span>
                    <span className="text-[11px] text-[#71717a] font-mono truncate max-w-xs hidden sm:inline">
                      {JSON.stringify(call.arguments)}
                    </span>
                  </div>

                  <div className="flex items-center space-x-2 text-[11px] text-[#71717a]">
                    <span className="flex items-center space-x-1">
                      <Clock className="h-3 w-3" />
                      <span>{call.duration_ms}ms</span>
                    </span>
                    <span
                      className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${
                        isSuccess
                          ? 'bg-emerald-50 text-emerald-700'
                          : 'bg-red-50 text-red-700'
                      }`}
                    >
                      {call.status}
                    </span>
                  </div>
                </div>

                {isExpanded && (
                  <div className="p-3 bg-[#ffffff] border-t border-[#e4e2dd] text-xs font-mono space-y-2.5">
                    <div>
                      <span className="text-[#71717a] block text-[11px] font-sans font-medium mb-1">
                        Arguments:
                      </span>
                      <pre className="p-2 bg-[#f4f2ee] rounded text-[#18181b] overflow-x-auto text-[11px]">
                        {JSON.stringify(call.arguments, null, 2)}
                      </pre>
                    </div>

                    <div>
                      <span className="text-[#71717a] block text-[11px] font-sans font-medium mb-1">
                        Result:
                      </span>
                      <pre className="p-2 bg-[#f4f2ee] rounded text-[#18181b] overflow-x-auto max-h-56 text-[11px]">
                        {typeof call.result === 'string'
                          ? call.result
                          : JSON.stringify(call.result, null, 2)}
                      </pre>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
