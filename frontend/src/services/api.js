import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
});

/**
 * Execute Python code with runtime tracing.
 * @param {string} code - Python source code
 * @param {string} input - Optional stdin data
 * @returns {Promise<object>} - Execution result
 */
export async function executeCode(code, input = '') {
  const response = await api.post('/execute', { code, input });
  return response.data;
}

/**
 * Check backend and sandbox health.
 * @returns {Promise<object>} - Health status
 */
export async function checkHealth() {
  const response = await api.get('/health');
  return response.data;
}

export default api;
