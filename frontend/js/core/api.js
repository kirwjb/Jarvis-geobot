import { API, tg } from './state.js?v=1791475344';

export async function request(path, options = {}) {
  const headers = {
    Accept: 'application/json',
    'ngrok-skip-browser-warning': 'true',
    ...(options.body ? { 'Content-Type': 'application/json' } : {}),
    ...(options.headers || {})
  };
  headers['ngrok-skip-browser-warning'] = 'true';
  const authPayload = tg?.initData || (window.JARVIS_MOCK_AUTH ? 'mock_auth' : '');
  if (authPayload) headers.Authorization = `tma ${authPayload}`;
  const response = await fetch(`${API}${path}`, { ...options, headers });
  let data = null;
  try { data = await response.json(); } catch (_) {}
  if (!response.ok) throw new Error(data?.detail || `HTTP ${response.status}`);
  return data;
}
