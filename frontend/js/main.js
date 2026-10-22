import { tg, state, persist } from './core/state.js?v=20261017-010';
import { applyTheme, syncTelegramTheme } from './ui/theme.js?v=20261017-010';
import { applyLanguage } from './ui/language.js?v=20261017-010';
import { go } from './core/router.js?v=20261017-010';
import { loadRegions, renderTags } from './features/travel.js?v=20261017-010';
import { renderWeatherCityChips } from './features/weather.js?v=20261017-010';
import { loadFavorites } from './features/favorites.js?v=20261017-010';
import { updateFab } from './features/route.js?v=20261017-010';
import { bindAppEvents } from './app/events.js?v=20261017-010';
import { request } from './core/api.js?v=20261017-010';

function initTelegram() {
  if (!tg) return;
  try {
    tg.ready();
    tg.expand();
    syncTelegramTheme();
  } catch (_) {}
}

async function restoreInitialData() {
  await Promise.all([loadRegions(), loadFavorites()]);
  if (!state.region) return;
  try {
    state.cities = await request(`/cities/${encodeURIComponent(state.region)}`) || [];
  } catch (_) {
    state.cities = [];
  }
}

async function init() {
  initTelegram();
  bindAppEvents();
  const savedTheme = localStorage.getItem('jarvis-theme');
  const initialTheme = savedTheme || tg?.colorScheme || 'dark';
  applyTheme(initialTheme, false);
  applyLanguage(localStorage.getItem('jarvis-language') || 'RU', false);
  renderTags();
  renderWeatherCityChips();
  updateFab();
  go('splash', { save: false });
  await restoreInitialData();
  persist();
}

init().catch((error) => console.error('JARVIS init failed', error));
