import React from 'react';

export default function ErrorCard({ error, analysis }) {
  if (!error) return null;

  return (
    <div className="p-3 border-t border-red-900/50 bg-red-950/30">
      <div className="flex items-center gap-2 mb-2">
        <span className="text-red-400 font-bold text-sm">
          {error.type}
        </span>
        <span className="text-xs text-gray-500">
          at line {error.line}
        </span>
        {analysis?.confidence != null && (
          <span
            className={`text-xs px-1.5 py-0.5 rounded ${
              analysis.confidence >= 0.8
                ? 'bg-green-900/30 text-green-400'
                : analysis.confidence >= 0.4
                ? 'bg-yellow-900/30 text-yellow-400'
                : 'bg-gray-800 text-gray-400'
            }`}
          >
            {(analysis.confidence * 100).toFixed(0)}% confidence
          </span>
        )}
      </div>
      <p className="text-red-300 text-sm mb-2">{error.message}</p>

      {/* Analysis evidence */}
      {analysis && analysis.category !== 'unknown' && (
        <div className="mt-2 space-y-1 text-xs text-gray-400">
          {analysis.sequence_variable && (
            <div>
              Sequence: <span className="text-blue-300 font-mono">{analysis.sequence_variable}</span>
              {' '}(length: {analysis.sequence_length}, valid: {analysis.valid_index_range})
            </div>
          )}
          {analysis.index_variable && (
            <div>
              Index: <span className="text-blue-300 font-mono">{analysis.index_variable}</span>
              {' '}= {analysis.attempted_index}
            </div>
          )}
          {analysis.divisor_variable && (
            <div>
              Divisor: <span className="text-blue-300 font-mono">{analysis.divisor_variable}</span>
              {' '}= {analysis.divisor_value}
            </div>
          )}
          {analysis.requested_key && (
            <div>
              Requested key: <span className="text-blue-300 font-mono">{String(analysis.requested_key)}</span>
            </div>
          )}
          {analysis.available_keys && (
            <div>
              Available: [
              {analysis.available_keys.map((k, i) => (
                <span key={i}>
                  <span className="text-green-300 font-mono">{String(k)}</span>
                  {i < analysis.available_keys.length - 1 ? ', ' : ''}
                </span>
              ))}
              ]
            </div>
          )}
          {analysis.missing_name && (
            <div>
              Missing: <span className="text-blue-300 font-mono">{analysis.missing_name}</span>
            </div>
          )}
          {analysis.similar_variables && (
            <div>
              Did you mean:{' '}
              {analysis.similar_variables.map((v, i) => (
                <span key={i}>
                  <span className="text-green-300 font-mono">{v}</span>
                  {i < analysis.similar_variables.length - 1 ? ', ' : ''}
                </span>
              ))}
              ?
            </div>
          )}
          {analysis.involved_types && (
            <div>
              Types: {analysis.involved_types.join(', ')}
            </div>
          )}
        </div>
      )}

      {/* Traceback */}
      {error.traceback_frames && error.traceback_frames.length > 0 && (
        <details className="mt-2">
          <summary className="text-xs text-gray-500 cursor-pointer hover:text-gray-400">
            Traceback ({error.traceback_frames.length} frames)
          </summary>
          <div className="mt-1 space-y-0.5 text-xs font-mono text-gray-500">
            {error.traceback_frames.map((frame, i) => (
              <div key={i}>
                File "{frame.file?.split('/').pop()}", line {frame.line}, in {frame.function}
              </div>
            ))}
          </div>
        </details>
      )}
    </div>
  );
}
