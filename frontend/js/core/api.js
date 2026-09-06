import { API, tg } from './state.js';

export async function request(path, options = {}) {
  const headers = { Accept: 'application/json', ...(options.body ? {'Content-Type':'application/json'} : {}), ...(options.headers || {}) };
  if (tg?.initData) headers.Authorization = `tma ${tg.initData}`;
  const response = await fetch(`${API}${path}`, {...options, headers});
  let data = null;
  try { data = await response.json(); } catch (_) {}
  if (!response.ok) throw new Error(data?.detail || `HTTP ${response.status}`);
  return data;
}
