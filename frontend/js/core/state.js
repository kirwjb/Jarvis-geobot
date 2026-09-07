export const tg = window.Telegram?.WebApp || null;
export const API = '/api';
export const STORAGE_KEY = 'jarvis-geo-state-v3';

const saved = (() => {
  try { return JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}'); } catch { return {}; }
})();

// Feed pages are deliberately not restored between WebApp sessions.
// This prevents a stale pagination cursor/page from surviving a close/reopen.
export const state = {
  mode: saved.mode || 'travel', region: saved.region || null, city: saved.city || null,
  tags: new Set(saved.tags || []), favs: new Set((saved.favs || []).map(String)), route: Array.isArray(saved.route) ? saved.route : [],
  regions: [], cities: [], pois: [], weather: null, screen: 'splash',
  feed: null
};

export const TAGS = [
  ['architecture','Архитектура'], ['nature','Природа'], ['museum','Музеи'], ['church','Храмы'], ['castle','Замки'], ['monument','Памятники'], ['park','Парки']
].map(([id,name]) => ({id,name}));

export function persist() {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({
      mode: state.mode, region: state.region, city: state.city, tags: [...state.tags], favs: [...state.favs], route: state.route,
      screen: state.screen
    }));
  } catch (_) {}
}

export function clearAppCache() {
  try {
    localStorage.removeItem('jarvis-geo-state-v2');
    localStorage.removeItem(STORAGE_KEY);
    sessionStorage.clear();
  } catch (_) {}
}

export function telegramUserId() { const id = tg?.initDataUnsafe?.user?.id; return Number.isInteger(id) ? id : null; }
