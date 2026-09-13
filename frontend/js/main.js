import { tg, state, persist } from './core/state.js';
import { applyTheme } from './ui/theme.js';
import { applyLanguage } from './ui/language.js';
import { go } from './core/router.js';
import { loadRegions } from './features/travel.js';
import { loadFavorites, updateFab } from './features/places.js';
import { renderTags } from './features/travel.js';
import { bindAppEvents } from './app/events.js';
import { request } from './core/api.js';

/** Initialize Telegram WebApp capabilities before feature bootstrap. */
function initTelegram() {
  if (!tg) return;
  try { tg.ready(); tg.expand(); } catch (_) { /* Browser fallback. */ }
}

/** Restore persisted application data needed by the initial screen. */
async function restoreInitialData() {
  await Promise.all([loadRegions(), loadFavorites()]);
  if (!state.region) return;
  try {
    state.cities = await request(`/cities/${encodeURIComponent(state.region)}`) || [];
  } catch (_) {
    state.cities = [];
  }
}

/** Bootstrap the shell, global event graph, language, theme and initial API data. */
async function init() {
  initTelegram();
  bindAppEvents();
  applyTheme(localStorage.getItem('jarvis-theme') || 'dark', false);
  applyLanguage(localStorage.getItem('jarvis-language') || 'RU', false);
  renderTags();
  updateFab();
  go('splash', { save: false });
  await restoreInitialData();
  persist();
}

init().catch((error) => console.error('JARVIS init failed', error));
