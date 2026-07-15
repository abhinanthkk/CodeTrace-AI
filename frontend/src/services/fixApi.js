import axios from 'axios';

const BACKEND_URL = import.meta.env.VITE_API_URL || '/api';

const fixClient = axios.create({
  baseURL: BACKEND_URL,
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
});

/**
 * Request a fix proposal for selected diagnostics.
 * @param {string} code - Full Python source code
 * @param {string[]} diagnosticIds - IDs of diagnostics to fix
 * @returns {Promise<object>} - Fix result
 */
export async function requestFix(code, diagnosticIds = []) {
  const response = await fixClient.post('/fix', { code, diagnostic_ids: diagnosticIds });
  return response.data;
}

export default fixClient;
