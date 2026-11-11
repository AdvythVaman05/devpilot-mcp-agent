import React, { useState, useRef, useEffect } from 'react';
import type { ExecutionEvent } from '../types';

interface ExecutionTraceProps {
  events: ExecutionEvent[];
}

export const ExecutionTrace: React.FC<ExecutionTraceProps> = ({ events }) => {
  const [selectedCategory, setSelectedCategory] = useState<string>('ALL');
  const [expandedEvents, setExpandedEvents] = useState<Record<string, boolean>>({});
  const [autoScroll, setAutoScroll] = useState<boolean>(true);
  const containerRef = useRef<HTMLDivElement | null>(null);

  // Auto-scroll to bottom on new events
  useEffect(() => {
    if (autoScroll && containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [events, autoScroll]);

  const toggleExpand = (id: string) => {
    setExpandedEvents((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const filteredEvents = selectedCategory === 'ALL'
    ? events
    : events.filter((e) => e.category === selectedCategory);

  const categories = ['ALL', 'AGENT', 'MCP', 'TOOL', 'TEST', 'APPROVAL', 'VERIFICATION'];

  const getCategoryBadge = (category: string) => {
    switch (category) {
      case 'AGENT':
        return 'bg-blue-50 text-blue-700 border-blue-200';
      case 'MCP':
        return 'bg-indigo-50 text-indigo-700 border-indigo-200';
      case 'TOOL':
        return 'bg-amber-50 text-amber-700 border-amber-200';
      case 'TEST':
        return 'bg-purple-50 text-purple-700 border-purple-200';
      case 'APPROVAL':
        return 'bg-rose-50 text-rose-700 border-rose-200';
      case 'VERIFICATION':
        return 'bg-emerald-50 text-emerald-700 border-emerald-200';
      case 'ERROR':
        return 'bg-red-50 text-red-700 border-red-200';
      default:
        return 'bg-stone-50 text-zinc-700 border-stone-200';
    }
  };

  return (
    <div className="bg-white rounded-xl border border-stone-200 shadow-xs overflow-hidden flex flex-col h-[520px]">
      {/* Trace Header & Filter Bar */}
      <div className="px-5 py-3 border-b border-stone-100 bg-stone-50/70 flex flex-wrap items-center justify-between gap-2 shrink-0">
        <div className="flex items-center gap-2">
          <div className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse"></div>
          <h2 className="text-sm font-semibold text-zinc-900 tracking-tight">
            Live Execution Trace
          </h2>
          <span className="text-xs font-mono text-zinc-600 bg-stone-100 px-2 py-0.5 rounded border border-stone-200">
            {filteredEvents.length} events
          </span>
        </div>

        <div className="flex items-center gap-2">
          {/* Category Filter Pills */}
          <div className="flex items-center gap-1 bg-stone-100 p-0.5 rounded-lg border border-stone-200 text-[11px]">
            {categories.map((cat) => (
              <button
                key={cat}
                type="button"
                onClick={() => setSelectedCategory(cat)}
                className={`px-2 py-0.5 rounded-md font-semibold transition-all ${
                  selectedCategory === cat
                    ? 'bg-white text-zinc-900 shadow-xs'
                    : 'text-zinc-700 hover:text-zinc-900'
                }`}
              >
                {cat}
              </button>
            ))}
          </div>

          {/* Auto-scroll toggle */}
          <button
            type="button"
            onClick={() => setAutoScroll(!autoScroll)}
            className={`text-[11px] font-medium px-2 py-1 rounded border transition-colors ${
              autoScroll
                ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
                : 'bg-stone-50 text-zinc-600 border-stone-200'
            }`}
            title="Auto-scroll on new events"
          >
            {autoScroll ? 'Scroll: ON' : 'Scroll: OFF'}
          </button>
        </div>
      </div>

      {/* Events Stream */}
      <div
        ref={containerRef}
        className="flex-1 overflow-y-auto p-4 space-y-2.5 bg-stone-50/30 divide-y-0"
      >
        {filteredEvents.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center p-6 text-zinc-600">
            <div className="text-2xl mb-2">📜</div>
            <p className="text-xs font-semibold text-zinc-700">No execution events recorded yet</p>
            <p className="text-[11px] max-w-xs text-zinc-600 mt-1">
              Launch an autonomous investigation or reset the repository to stream live MCP tool calls and test traces.
            </p>
          </div>
        ) : (
          filteredEvents.map((evt) => {
            const isExpanded = expandedEvents[evt.id] || false;
            const hasData = evt.data && Object.keys(evt.data).length > 0;

            return (
              <div
                key={evt.id}
                className="bg-white rounded-lg border border-stone-200 p-3 shadow-2xs hover:border-stone-300 transition-colors"
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-[10px] text-zinc-600 font-medium shrink-0">
                      {evt.timestamp}
                    </span>
                    <span
                      className={`text-[10px] font-bold tracking-wider px-1.5 py-0.5 rounded border uppercase ${getCategoryBadge(
                        evt.category
                      )}`}
                    >
                      {evt.category}
                    </span>
                    <span className="text-xs font-semibold text-zinc-900 truncate">
                      {evt.title}
                    </span>
                  </div>

                  {hasData && (
                    <button
                      type="button"
                      onClick={() => toggleExpand(evt.id)}
                      className="text-[10px] font-mono text-zinc-600 hover:text-zinc-800 bg-stone-50 hover:bg-stone-100 px-1.5 py-0.5 rounded border border-stone-200 transition-colors shrink-0"
                    >
                      {isExpanded ? 'Hide Payload' : 'View Payload'}
                    </button>
                  )}
                </div>

                {evt.detail && (
                  <p className="mt-1 text-[11px] text-zinc-700 leading-relaxed font-mono pl-14 break-all">
                    {evt.detail}
                  </p>
                )}

                {isExpanded && hasData && (
                  <div className="mt-2.5 ml-14 p-2.5 rounded-md bg-stone-900 text-stone-100 font-mono text-[10px] overflow-x-auto border border-stone-800">
                    <div className="text-[9px] font-sans font-semibold text-orange-400 uppercase tracking-wider mb-1">
                      Event Data Payload (Sanitized)
                    </div>
                    <pre className="whitespace-pre-wrap break-all">
                      {typeof evt.data === 'string'
                        ? evt.data
                        : JSON.stringify(evt.data, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
