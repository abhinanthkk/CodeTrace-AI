import React from 'react';

export default function AIExplanation({ explanation, analysis, error, status }) {
  // Show nothing for successful executions
  if (status === 'success' || !error) {
    if (!analysis) return null;
  }

  // Deterministic explanation from analysis
  const analysisMsg = analysis?.explanation || '';

  // AI explanation (when available)
  const hasAI = explanation?.summary || explanation?.what_failed;

  return (
    <div className="h-full overflow-auto">
      <div className="px-4 py-2 text-xs text-gray-500 bg-gray-900 border-b border-gray-800">
        {hasAI ? 'AI Explanation' : 'Analysis'}
        {!hasAI && analysisMsg && (
          <span className="ml-2 text-gray-600">
            (deterministic — no AI API key configured)
          </span>
        )}
      </div>

      <div className="p-4 space-y-3 text-sm">
        {/* AI explanation takes precedence */}
        {hasAI ? (
          <>
            {explanation.summary && (
              <Section title="Summary">
                <p className="text-gray-300">{explanation.summary}</p>
              </Section>
            )}
            {explanation.what_failed && (
              <Section title="What Failed">
                <p className="text-gray-300">{explanation.what_failed}</p>
              </Section>
            )}
            {explanation.why && (
              <Section title="Why It Failed">
                <p className="text-gray-300">{explanation.why}</p>
              </Section>
            )}
            {explanation.execution_sequence && (
              <Section title="Execution Sequence">
                <p className="text-gray-400 font-mono text-xs whitespace-pre-wrap">
                  {explanation.execution_sequence}
                </p>
              </Section>
            )}
            {explanation.suggested_fix && (
              <Section title="Suggested Fix">
                <p className="text-green-400">{explanation.suggested_fix}</p>
              </Section>
            )}
            {explanation.corrected_code && (
              <Section title="Corrected Code">
                <pre className="bg-gray-900 rounded p-3 text-xs font-mono text-gray-300 overflow-auto">
                  {explanation.corrected_code}
                </pre>
              </Section>
            )}
          </>
        ) : analysisMsg ? (
          <Section title="What Happened">
            <p className="text-gray-300">{analysisMsg}</p>
          </Section>
        ) : (
          <p className="text-gray-600 italic">
            {status === 'syntax_error'
              ? 'Fix the syntax error to see runtime analysis.'
              : 'No analysis available.'}
          </p>
        )}

        {/* AI not available note */}
        {!hasAI && error && (
          <p className="text-xs text-gray-600 border-t border-gray-800 pt-2 mt-3">
            Add an AI API key (OpenAI or Gemini) in .env to get AI-powered
            explanations with suggested fixes and corrected code.
          </p>
        )}
      </div>
    </div>
  );
}

function Section({ title, children }) {
  return (
    <div>
      <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-1">
        {title}
      </h4>
      {children}
    </div>
  );
}
