import axios from 'axios';

// In production (Vercel), use the backend URL from env var.
// In development (Vite), use the local proxy.
const BACKEND_URL = import.meta.env.VITE_API_URL || '/api';

const api = axios.create({
  baseURL: BACKEND_URL,
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
});

/**
 * Execute Python code with runtime tracing.
 */
export async function executeCode(code, input = '') {
  const response = await api.post('/execute', { code, input });
  return response.data;
}

/**
 * Check backend and sandbox health.
 */
export async function checkHealth() {
  const response = await api.get('/health');
  return response.data;
}

export default api;
