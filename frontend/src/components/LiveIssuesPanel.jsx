import React from 'react';

const SEVERITY_ICONS = {
  error: { icon: '●', color: 'text-red-400', bg: 'bg-red-900/20', label: 'Error' },
  warning: { icon: '●', color: 'text-yellow-400', bg: 'bg-yellow-900/20', label: 'Warning' },
  info: { icon: '●', color: 'text-blue-400', bg: 'bg-blue-900/20', label: 'Info' },
};

export default function LiveIssuesPanel({
  diagnostics,
  onSelectDiagnostic,
  onQuickFix,
  selectedDiagnosticId,
}) {
  // Sort: errors first, then by line
  const sorted = [...diagnostics].sort((a, b) => {
    const sev = { error: 0, warning: 1, info: 2 };
    const sa = sev[a.severity] ?? 2;
    const sb = sev[b.severity] ?? 2;
    if (sa !== sb) return sa - sb;
    return a.line - b.line;
  });

  const issues = sorted.filter((d) => d.severity === 'error' || d.severity === 'warning');

  if (issues.length === 0) {
    return (
      <div className="h-full flex flex-col">
        <div className="px-3 py-1.5 text-xs text-gray-500 bg-gray-900 border-b border-gray-800 flex justify-between">
          <span>Live Issues</span>
          <span className="text-green-400">No issues</span>
        </div>
        <div className="flex-1 flex items-center justify-center text-gray-600 text-xs p-3">
          All clear — no errors or warnings detected.
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      <div className="px-3 py-1.5 text-xs text-gray-500 bg-gray-900 border-b border-gray-800 flex justify-between">
        <span>Live Issues</span>
        <span className="text-orange-400">
          {issues.length} issue{issues.length !== 1 ? 's' : ''}
        </span>
      </div>
      <div className="flex-1 overflow-auto">
        {issues.map((diag) => {
          const sev = SEVERITY_ICONS[diag.severity] || SEVERITY_ICONS.info;
          const isSelected = selectedDiagnosticId === diag.id;

          return (
            <div
              key={diag.id}
              className={`px-3 py-2 border-b border-gray-800/50 cursor-pointer transition-colors text-sm ${
                isSelected
                  ? 'bg-blue-900/30 border-l-2 border-l-blue-500'
                  : 'hover:bg-gray-900/50 border-l-2 border-l-transparent'
              }`}
              onClick={() => onSelectDiagnostic(diag)}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-start gap-2 min-w-0">
                  <span className={`mt-0.5 flex-shrink-0 ${sev.color}`}>{sev.icon}</span>
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs text-gray-400">{diag.code}</span>
                      <span className="text-xs text-gray-600">Line {diag.line}</span>
                    </div>
                    <p className="text-xs text-gray-300 mt-0.5 truncate">{diag.message}</p>
                  </div>
                </div>

                {diag.fix_available && diag.fix_type !== 'manual' && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      if (onQuickFix) onQuickFix(diag);
                    }}
                    className="flex-shrink-0 text-xs px-2 py-0.5 rounded bg-blue-600/30 text-blue-300 hover:bg-blue-600/50 transition-colors"
                  >
                    Fix
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
