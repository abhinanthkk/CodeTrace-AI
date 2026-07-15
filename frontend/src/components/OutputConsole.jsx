import React from 'react';

const STATUS_LABELS = {
  success: { text: 'Success', color: 'text-green-400', bg: 'bg-green-900/30' },
  runtime_error: { text: 'Runtime Error', color: 'text-red-400', bg: 'bg-red-900/30' },
  syntax_error: { text: 'Syntax Error', color: 'text-red-400', bg: 'bg-red-900/30' },
  timeout: { text: 'Timeout', color: 'text-yellow-400', bg: 'bg-yellow-900/30' },
  memory_limit: { text: 'Memory Limit', color: 'text-yellow-400', bg: 'bg-yellow-900/30' },
  output_limit: { text: 'Output Limit', color: 'text-yellow-400', bg: 'bg-yellow-900/30' },
  sandbox_error: { text: 'Sandbox Error', color: 'text-orange-400', bg: 'bg-orange-900/30' },
};

export default function OutputConsole({ stdout, stderr, status }) {
  const statusInfo = STATUS_LABELS[status] || null;

  return (
    <div className="h-full flex flex-col">
      <div className="px-3 py-1 text-xs text-gray-500 bg-gray-900 border-b border-gray-800 flex items-center justify-between">
        <span>Output Console</span>
        {statusInfo && (
          <span className={`text-xs px-2 py-0.5 rounded ${statusInfo.bg} ${statusInfo.color}`}>
            {statusInfo.text}
          </span>
        )}
      </div>
      <div className="flex-1 overflow-auto p-3 font-mono text-sm">
        {stdout ? (
          <pre className="text-green-400 whitespace-pre-wrap break-words">{stdout}</pre>
        ) : !stderr && !status ? (
          <span className="text-gray-600 italic">Run code to see output...</span>
        ) : null}
        {stderr && (
          <pre className="text-red-400 whitespace-pre-wrap break-words mt-1">{stderr}</pre>
        )}
        {!stdout && !stderr && status && status !== 'success' && (
          <span className="text-gray-500 italic">No output captured.</span>
        )}
      </div>
    </div>
  );
}
