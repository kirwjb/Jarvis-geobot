import { tg, state, persist } from './core/state.js?v=1791475344';
import { applyTheme, syncTelegramTheme } from './ui/theme.js?v=1791475344';
import { applyLanguage } from './ui/language.js?v=1791475344';
import { go } from './core/router.js?v=1791475344';
import { loadRegions, renderTags } from './features/travel.js?v=1791475344';
import { loadFavorites } from './features/favorites.js?v=1791475344';
import { updateFab } from './features/route.js?v=1791475344';
import { bindAppEvents } from './app/events.js?v=1791475344';
import { request } from './core/api.js?v=1791475344';


/** Force bust CSS cache since Telegram WebApp aggressively caches index.html */
function bustCssCache() {
  const version = Date.now();
  document.querySelectorAll('link[rel="stylesheet"]').forEach(link => {
    const url = new URL(link.href);
    if (!url.searchParams.has('dynamic_v')) {
      url.searchParams.set('dynamic_v', version);
      link.href = url.toString();
    }
  });
}

/** Initialize Telegram WebApp capabilities before feature bootstrap. */
function initTelegram() {
  if (!tg) return;
  try {
    tg.ready();
    tg.expand();
    syncTelegramTheme();
  } catch (_) { /* Browser fallback. */ }
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
  bustCssCache();
  initTelegram();
  bindAppEvents();
  const savedTheme = localStorage.getItem('jarvis-theme');
  const initialTheme = savedTheme || tg?.colorScheme || 'dark';
  applyTheme(initialTheme, false);
  applyLanguage(localStorage.getItem('jarvis-language') || 'RU', false);
  renderTags();
  updateFab();
  go('splash', { save: false });
  await restoreInitialData();
  persist();
}

init().catch((error) => console.error('JARVIS init failed', error));
