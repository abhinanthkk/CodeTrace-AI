import axios from 'axios';

const BACKEND_URL = import.meta.env.VITE_API_URL || '/api';

const lintClient = axios.create({
  baseURL: BACKEND_URL,
  timeout: 5000,
  headers: { 'Content-Type': 'application/json' },
});

/**
 * Run Ruff static analysis on Python code.
 * @param {string} code - Python source code
 * @param {object} options - { signal: AbortSignal }
 * @returns {Promise<object>} - { status, diagnostics, ruff_available }
 */
export async function lintCode(code, options = {}) {
  const response = await lintClient.post('/lint', { code }, { signal: options.signal });
  return response.data;
}

export default lintClient;
