import React from 'react';

export default function FixPreview({ fixResult, onApply, onReject, onRunVerify, applying, verifying }) {
  if (!fixResult) return null;

  const { title, explanation, confidence, fixed_code: fixedCode, original_code: originalCode, fix_type: fixType, requires_ai: requiresAi, status } = fixResult;

  if (status === 'ai_unavailable') {
    return (
      <div className="border-t border-gray-800 bg-gray-900 p-4">
        <div className="text-yellow-400 text-sm font-medium mb-1">AI Not Configured</div>
        <p className="text-gray-400 text-xs">{explanation || 'Add an AI API key for contextual block fixes.'}</p>
        <p className="text-gray-600 text-xs mt-2">Quick fixes (like typo corrections) still work without AI.</p>
      </div>
    );
  }

  if (status === 'no_diagnostics' || status === 'no_fix_available') {
    return (
      <div className="border-t border-gray-800 bg-gray-900 p-4">
        <div className="text-gray-400 text-sm">{title}</div>
        <p className="text-gray-500 text-xs mt-1">{explanation}</p>
      </div>
    );
  }

  return (
    <div className="border-t border-gray-800 bg-gray-900">
      {/* Header */}
      <div className="px-4 py-2 flex items-center justify-between border-b border-gray-800">
        <div className="flex items-center gap-2">
          <span className={`text-xs px-2 py-0.5 rounded ${fixType === 'quick' ? 'bg-green-900/30 text-green-400' : 'bg-purple-900/30 text-purple-400'}`}>
            {fixType === 'quick' ? 'QUICK FIX' : 'AI BLOCK FIX'}
          </span>
          {requiresAi && <span className="text-xs text-purple-400">AI-assisted</span>}
          {confidence > 0 && (
            <span className="text-xs text-gray-500">
              {(confidence * 100).toFixed(0)}% confidence
            </span>
          )}
        </div>
        <div className="flex gap-2">
          <button
            onClick={onReject}
            className="px-3 py-1 text-xs rounded border border-gray-700 text-gray-400 hover:bg-gray-800 transition-colors"
          >
            Reject
          </button>
          {onRunVerify && (
            <button
              onClick={onRunVerify}
              disabled={verifying}
              className="px-3 py-1 text-xs rounded border border-blue-700 text-blue-400 hover:bg-blue-900/30 transition-colors disabled:opacity-50"
            >
              {verifying ? 'Running...' : 'Run & Verify'}
            </button>
          )}
          <button
            onClick={onApply}
            disabled={applying}
            className="px-3 py-1 text-xs rounded bg-blue-600 text-white hover:bg-blue-500 disabled:opacity-50 transition-colors"
          >
            {applying ? 'Applying...' : 'Apply Fix'}
          </button>
        </div>
      </div>

      {/* Title & Explanation */}
      <div className="px-4 py-2">
        <h4 className="text-sm font-medium text-gray-200">{title}</h4>
        {explanation && (
          <p className="text-xs text-gray-400 mt-1">{explanation}</p>
        )}
      </div>

      {/* Diff view */}
      {fixedCode && originalCode && fixedCode !== originalCode && (
        <div className="px-4 pb-3">
          <div className="text-xs text-gray-500 mb-1">Changes:</div>
          <div className="bg-gray-950 rounded border border-gray-800 overflow-auto max-h-48">
            <pre className="p-3 text-xs font-mono">
              {renderDiff(originalCode, fixedCode)}
            </pre>
          </div>
        </div>
      )}

      {fixedCode && !originalCode && (
        <div className="px-4 pb-3">
          <div className="text-xs text-gray-500 mb-1">Fixed code:</div>
          <div className="bg-gray-950 rounded border border-gray-800 overflow-auto max-h-48">
            <pre className="p-3 text-xs font-mono text-gray-300">{fixedCode}</pre>
          </div>
        </div>
      )}
    </div>
  );
}

function renderDiff(original, fixed) {
  const origLines = original.split('\n');
  const fixedLines = fixed.split('\n');
  const maxLen = Math.max(origLines.length, fixedLines.length);

  const result = [];
  for (let i = 0; i < maxLen; i++) {
    const origLine = origLines[i];
    const fixedLine = fixedLines[i];

    if (origLine === fixedLine) {
      result.push(
        <div key={i} className="text-gray-500">
          {'  '}{origLine || ''}
        </div>
      );
    } else {
      if (origLine !== undefined) {
        result.push(
          <div key={`orig-${i}`} className="text-red-400 bg-red-900/20">
            {'- '}{origLine}
          </div>
        );
      }
      if (fixedLine !== undefined) {
        result.push(
          <div key={`fix-${i}`} className="text-green-400 bg-green-900/20">
            {'+ '}{fixedLine}
          </div>
        );
      }
    }
  }
  return result;
}
