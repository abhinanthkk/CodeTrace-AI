import React, { useState, useCallback, useRef } from 'react';
import CodeEditor from '../components/CodeEditor';
import InputPanel from '../components/InputPanel';
import ExecutionTimeline from '../components/ExecutionTimeline';
import VariableInspector from '../components/VariableInspector';
import OutputConsole from '../components/OutputConsole';
import ErrorCard from '../components/ErrorCard';
import AIExplanation from '../components/AIExplanation';
import LiveStatus from '../components/LiveStatus';
import LiveIssuesPanel from '../components/LiveIssuesPanel';
import { executeCode } from '../services/api';
import { requestFix } from '../services/fixApi';
import useLiveLint from '../hooks/useLiveLint';
import FixPreview from '../components/FixPreview';

export default function DebuggerPage() {
  const [code, setCode] = useState(
    'name = "Abhinanth"\n\nprint(nam)\n'
  );
  const [stdin, setStdin] = useState('');
  const [result, setResult] = useState(null);
  const [selectedStep, setSelectedStep] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selectedDiagId, setSelectedDiagId] = useState(null);
  const editorRef = useRef(null);

  // Live lint
  const { diagnostics, lintStatus, runLint } = useLiveLint(code);
  const issueCount = diagnostics.filter(
    (d) => d.severity === 'error' || d.severity === 'warning'
  ).length;

  // Fix state
  const [fixResult, setFixResult] = useState(null);
  const [applying, setApplying] = useState(false);
  const [verifying, setVerifying] = useState(false);
  const [verifyResult, setVerifyResult] = useState(null);
  const [codeBeforeFix, setCodeBeforeFix] = useState(null);

  const handleAnalyze = useCallback(async () => {
    setLoading(true);
    setError(null);
    setResult(null);
    setSelectedStep(null);

    try {
      const data = await executeCode(code, stdin);
      setResult(data);

      if (data.error && data.timeline.length > 0) {
        const errStep = data.timeline.find((s) => s.event === 'exception');
        if (errStep) {
          setSelectedStep(errStep.step);
        }
      }
    } catch (err) {
      const msg = err.response?.data?.detail || err.message || 'Request failed';
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, [code, stdin]);

  const handleSelectDiagnostic = useCallback((diag) => {
    setSelectedDiagId(diag.id);
    if (editorRef.current) {
      editorRef.current.revealLineInCenter(diag.line);
      editorRef.current.setPosition({ lineNumber: diag.line, column: diag.column || 1 });
    }
  }, []);

  const handleEditorMount = useCallback((editor) => {
    editorRef.current = editor;
  }, []);

  const handleQuickFix = useCallback(async (diag) => {
    setFixResult(null);
    setVerifyResult(null);
    try {
      const result = await requestFix(code, [diag.id]);
      setFixResult(result);
      setCodeBeforeFix(code);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Fix request failed');
    }
  }, [code]);

  const handleApplyFix = useCallback(() => {
    if (!fixResult?.fixed_code) return;
    if (codeBeforeFix !== code) {
      setError('Code changed after fix was generated. Re-analyze the current code.');
      return;
    }
    setApplying(true);
    setCode(fixResult.fixed_code);
    setFixResult(null);
    setCodeBeforeFix(null);
    setVerifyResult(null);
    setApplying(false);
    // Trigger re-lint
    setTimeout(() => runLint(fixResult.fixed_code), 100);
  }, [fixResult, code, codeBeforeFix, runLint]);

  const handleRejectFix = useCallback(() => {
    setFixResult(null);
    setCodeBeforeFix(null);
    setVerifyResult(null);
  }, []);

  const handleRunVerify = useCallback(async () => {
    if (!fixResult?.fixed_code) return;
    setVerifying(true);
    setVerifyResult(null);
    try {
      const data = await executeCode(fixResult.fixed_code, stdin);
      setVerifyResult(data);
      if (data.error && data.timeline.length > 0) {
        const errStep = data.timeline.find((s) => s.event === 'exception');
        if (errStep) setSelectedStep(errStep.step);
      }
    } catch (err) {
      setVerifyResult({ status: 'error', stderr: err.message });
    } finally {
      setVerifying(false);
    }
  }, [fixResult, stdin]);

  const handleReset = useCallback(() => {
    setResult(null);
    setSelectedStep(null);
    setError(null);
    setSelectedDiagId(null);
    setFixResult(null);
    setVerifyResult(null);
    setCodeBeforeFix(null);
  }, []);

  const selectedData =
    selectedStep && result
      ? result.timeline.find((s) => s.step === selectedStep)
      : null;

  const errorLine = result?.error?.line || null;

  return (
    <div className="h-screen flex flex-col bg-gray-950 text-gray-100">
      {/* Top navigation */}
      <header className="flex items-center justify-between px-4 py-2 border-b border-gray-800 bg-gray-900">
        <div className="flex items-center gap-3">
          <span className="text-xl font-bold text-blue-400">CodeTrace AI</span>
          <span className="text-sm text-gray-500 hidden sm:inline">
            — Why did my code fail?
          </span>
          <LiveStatus lintStatus={lintStatus} issueCount={issueCount} />
        </div>
        <div className="flex gap-2">
          <button
            onClick={handleReset}
            className="px-3 py-1.5 text-sm rounded border border-gray-700 text-gray-300 hover:bg-gray-800 transition-colors"
          >
            Reset
          </button>
          <button
            onClick={handleAnalyze}
            disabled={loading || !code.trim()}
            className="px-4 py-1.5 text-sm rounded bg-blue-600 text-white hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium"
          >
            {loading ? 'Running...' : 'Analyze'}
          </button>
        </div>
      </header>

      {/* Main workspace */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left: Code Editor + Input + Output */}
        <div className="w-1/2 flex flex-col border-r border-gray-800">
          <div className="flex-1 min-h-0">
            <CodeEditor
              code={code}
              onChange={setCode}
              selectedLine={selectedData?.line || null}
              errorLine={errorLine}
              readOnly={loading}
              lintDiagnostics={diagnostics}
              onEditorMount={handleEditorMount}
            />
          </div>
          <div className="flex flex-col border-t border-gray-800" style={{ maxHeight: '30%' }}>
            <div className="h-24">
              <InputPanel value={stdin} onChange={setStdin} disabled={loading} />
            </div>
            <div className="flex-1 min-h-[80px] border-t border-gray-800">
              <OutputConsole
                stdout={result?.stdout || ''}
                stderr={result?.stderr || ''}
                status={result?.status || null}
              />
            </div>
          </div>
        </div>

        {/* Right: Timeline + Live Issues */}
        <div className="w-1/2 flex flex-col">
          <div className="h-2/5 border-b border-gray-800 overflow-hidden">
            <LiveIssuesPanel
              diagnostics={diagnostics}
              onSelectDiagnostic={handleSelectDiagnostic}
              onQuickFix={handleQuickFix}
              selectedDiagnosticId={selectedDiagId}
            />
          </div>
          <div className="h-3/5 flex flex-col overflow-hidden">
            <div className="flex-1 border-b border-gray-800 overflow-hidden">
              <ExecutionTimeline
              timeline={result?.timeline || []}
              status={result?.status || null}
              selectedStep={selectedStep}
              onSelectStep={setSelectedStep}
            />
            </div>
            <div className="flex-1 flex flex-col overflow-hidden">
              {selectedData && (
              <div className="flex-1 overflow-auto border-b border-gray-800">
                <VariableInspector
                  variables={selectedData.variables || {}}
                  changes={selectedData.changes || {}}
                />
              </div>
            )}
            {result?.error && (
              <div className="overflow-auto" style={{ maxHeight: selectedData ? '35%' : '100%' }}>
                <ErrorCard error={result.error} analysis={result.analysis} />
              </div>
            )}
            </div>
          </div>
          </div>
        </div>

      {/* Fix Preview */}
      {fixResult && (
        <FixPreview
          fixResult={fixResult}
          onApply={handleApplyFix}
          onReject={handleRejectFix}
          onRunVerify={handleRunVerify}
          applying={applying}
          verifying={verifying}
        />
      )}

      {/* Verification result */}
      {verifyResult && (
        <div className="border-t border-gray-800 bg-gray-900 p-3">
          <div className="flex items-center gap-2 text-sm">
            <span className={verifyResult.status === 'success' ? 'text-green-400' : 'text-red-400'}>
              {verifyResult.status === 'success' ? '✓ FIX VERIFIED' : '✗ FIX NOT VERIFIED'}
            </span>
            <span className="text-xs text-gray-500">
              {verifyResult.status === 'success'
                ? 'Program completed successfully.'
                : verifyResult.error
                  ? `${verifyResult.error.type || 'Error'} at line ${verifyResult.error.line}`
                  : 'Verification failed.'}
            </span>
          </div>
          {verifyResult.stdout && (
            <pre className="mt-1 text-xs text-green-400 font-mono">{verifyResult.stdout}</pre>
          )}
        </div>
      )}

      {/* Bottom: AI Explanation */}
      {result && (
        <div className="border-t border-gray-800 bg-gray-900" style={{ maxHeight: '25%' }}>
          <AIExplanation
            explanation={result.explanation}
            analysis={result.analysis}
            error={result.error}
            status={result.status}
          />
        </div>
      )}

      {/* Error banner */}
      {error && (
        <div className="fixed bottom-4 right-4 bg-red-900/90 border border-red-700 text-red-100 px-4 py-3 rounded-lg shadow-lg max-w-md">
          <div className="flex items-center justify-between gap-3">
            <span className="text-sm">{error}</span>
            <button onClick={() => setError(null)} className="text-red-300 hover:text-white">
              ✕
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
