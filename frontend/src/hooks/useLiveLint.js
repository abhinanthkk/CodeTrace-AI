import { useState, useEffect, useRef, useCallback } from 'react';
import { lintCode } from '../services/lintApi';

const DEBOUNCE_MS = 700;

/**
 * Hook: live lint Python code via Ruff.
 *
 * Features:
 * - Debounced: waits DEBOUNCE_MS after last keystroke
 * - Stale request protection: newer requests cancel older ones via AbortController
 * - Returns diagnostics, status, and a manual trigger
 */
export default function useLiveLint(code) {
  const [diagnostics, setDiagnostics] = useState([]);
  const [lintStatus, setLintStatus] = useState('live'); // 'live' | 'checking' | 'issues' | 'clean' | 'unavailable'
  const [ruffAvailable, setRuffAvailable] = useState(true);
  const timerRef = useRef(null);
  const abortRef = useRef(null);
  const requestIdRef = useRef(0);

  const runLint = useCallback(async (sourceCode) => {
    // Cancel any in-flight request
    if (abortRef.current) {
      abortRef.current.abort();
    }

    const controller = new AbortController();
    abortRef.current = controller;
    const currentId = ++requestIdRef.current;

    if (!sourceCode.trim()) {
      setDiagnostics([]);
      setLintStatus('live');
      return;
    }

    setLintStatus('checking');

    try {
      const result = await lintCode(sourceCode, { signal: controller.signal });

      // Ignore stale responses
      if (currentId !== requestIdRef.current) return;

      const diags = result.diagnostics || [];
      setDiagnostics(diags);
      setRuffAvailable(result.ruff_available !== false);

      // Count only errors and warnings for status
      const issues = diags.filter((d) => d.severity === 'error' || d.severity === 'warning');
      if (issues.length > 0) {
        setLintStatus('issues');
      } else {
        setLintStatus('clean');
      }
    } catch (err) {
      // Ignore aborted requests
      if (err?.name === 'CanceledError' || err?.code === 'ERR_CANCELED') return;
      if (currentId !== requestIdRef.current) return;

      setDiagnostics([]);
      setLintStatus('unavailable');
      setRuffAvailable(false);
    }
  }, []);

  // Debounced lint on code change
  useEffect(() => {
    if (timerRef.current) {
      clearTimeout(timerRef.current);
    }

    timerRef.current = setTimeout(() => {
      runLint(code);
    }, DEBOUNCE_MS);

    return () => {
      if (timerRef.current) {
        clearTimeout(timerRef.current);
      }
    };
  }, [code, runLint]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (abortRef.current) {
        abortRef.current.abort();
      }
    };
  }, []);

  return {
    diagnostics,
    lintStatus,
    ruffAvailable,
    runLint, // Manual trigger (e.g., after applying a fix)
  };
}
