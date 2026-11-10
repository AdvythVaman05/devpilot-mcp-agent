import React, { useState } from 'react';
import { FileText, Copy, Check, Download } from 'lucide-react';
import type { Report } from '../types';

interface EngineeringReportViewProps {
  report: Report | null;
}

export const EngineeringReportView: React.FC<EngineeringReportViewProps> = ({ report }) => {
  const [copied, setCopied] = useState(false);

  if (!report) return null;

  const handleCopy = () => {
    navigator.clipboard.writeText(report.full_markdown);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    const blob = new Blob([report.full_markdown], { type: 'text/markdown;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `DevPilot_Report_${report.session_id}.md`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="bg-[#ffffff] rounded-xl border border-[#e4e2dd] p-5 shadow-xs mb-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-[#e4e2dd]">
        <div className="flex items-center space-x-2.5">
          <div className="p-2 bg-[#ffedd5] text-[#ea580c] rounded-lg">
            <FileText className="h-5 w-5" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h3 className="font-semibold text-sm text-[#18181b]">
                Evidence-Backed Engineering Investigation Report
              </h3>
              <span className="text-xs px-2 py-0.5 rounded-full font-medium bg-emerald-50 text-emerald-800 border border-emerald-200">
                {report.verification_status}
              </span>
            </div>
            <p className="text-xs text-[#52525b]">
              Synthesized by DevPilot using real MCP tool traces and verified regression tests.
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          <button
            onClick={handleCopy}
            className="flex items-center space-x-1.5 px-3 py-1.5 text-xs font-medium text-[#18181b] bg-[#f4f2ee] hover:bg-[#e9e6df] rounded-md border border-[#e4e2dd] transition-colors"
          >
            {copied ? <Check className="h-3.5 w-3.5 text-emerald-600" /> : <Copy className="h-3.5 w-3.5 text-[#52525b]" />}
            <span>{copied ? 'Copied' : 'Copy Markdown'}</span>
          </button>
          <button
            onClick={handleDownload}
            className="flex items-center space-x-1.5 px-3 py-1.5 text-xs font-medium text-white bg-[#18181b] hover:bg-[#27272a] rounded-md transition-colors"
          >
            <Download className="h-3.5 w-3.5" />
            <span>Download .md</span>
          </button>
        </div>
      </div>

      {/* Markdown Content Presentation */}
      <div className="mt-4 p-4 rounded-lg bg-[#faf8f5] border border-[#e4e2dd] text-xs leading-relaxed text-[#18181b] overflow-x-auto">
        <pre className="font-mono whitespace-pre-wrap font-normal text-[11px] text-[#27272a]">
          {report.full_markdown}
        </pre>
      </div>
    </div>
  );
};
