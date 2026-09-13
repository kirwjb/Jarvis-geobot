import { state } from '../core/state.js';
import { $ } from '../ui/helpers.js';
import { toggleTheme } from '../ui/theme.js';
import { toggleLanguage } from '../ui/language.js';
import { go, initTelegramBackButton, bindNavigation } from '../core/router.js';
import { loadRegions, pickRegion, pickCity, toggleTag, filterRegions, filterCities, renderTags, startPlaces } from '../features/travel.js';
import { loadWeather, renderWeather } from '../features/weather.js';
import { loadFavorites, toggleFavorite, toggleRoute, openDetail, loadPage, updateFab } from '../features/places.js';
import { renderRoute, removeRoute, buildRoute, copyRoute, openRoute } from '../features/route.js';
import { installExtraNavigation } from '../features/navigation-extra.js';
import { loadGroups, openGroup, createGroup, invite, send, vote, toggleVoting, saveDate, proposePlace, submitProposal } from '../features/groups.js';

/** Dispatch a delegated click to the feature that owns the requested action. */
function handleClick(event) {
  const element = event.target.closest('[data-action]');
  if (!element || !document.body.contains(element)) return;
  const action = element.dataset.action;
  if (action === 'theme') { event.preventDefault(); toggleTheme(); return; }
  if (action === 'language') { event.preventDefault(); toggleLanguage(); return; }
  if (action === 'start') { event.preventDefault(); go('regions'); loadRegions(); return; }
  if (action === 'back') { event.preventDefault(); go(element.dataset.screen || 'regions'); return; }
  if (action === 'region') { pickRegion(element.dataset.id); return; }
  if (action === 'city') { event.preventDefault(); pickCity(element.dataset.city); return; }
  if (action === 'tag') { toggleTag(element.dataset.id); return; }
  if (action === 'show-places') { event.preventDefault(); startPlaces(); return; }
  if (action === 'choose-city') { state.mode = 'weather'; go('regions'); return; }
  if (action === 'weather-refresh') { loadWeather(); return; }
  if (action === 'page-prev' || action === 'page-next') { event.preventDefault(); loadPage(Number(element.dataset.page)); return; }
  if (action === 'favorite') { event.stopPropagation(); toggleFavorite(element.dataset.id); return; }
  if (action === 'route') { event.stopPropagation(); toggleRoute(element.dataset.id); return; }
  if (action === 'detail') { openDetail(element.dataset.id); return; }
  if (action === 'remove-route') { removeRoute(element.dataset.id); return; }
  if (action === 'build-route') { buildRoute(); return; }
  if (action === 'open-route') { openRoute(element.dataset.url); return; }
  if (action === 'copy-route') { copyRoute(element.dataset.url); return; }
  if (action === 'close-modal') { element.closest('.jarvis-modal')?.remove(); return; }
  if (action === 'groups') { event.preventDefault(); go('groups'); loadGroups(); return; }
  if (action === 'group-open') { openGroup(Number(element.dataset.id)); return; }
  if (action === 'group-create') { createGroup(); return; }
  if (action === 'group-invite') { invite(); return; }
  if (action === 'group-send') { send(); return; }
  if (action === 'group-date-save') { saveDate(); return; }
  if (action === 'group-propose') { proposePlace(); return; }
  if (action === 'group-propose-place') { submitProposal(element.dataset.place); return; }
  if (action === 'group-vote') { vote(element.dataset.place); return; }
  if (action === 'group-toggle-voting') { toggleVoting(); }
}

/** Route input changes to the search control owned by the travel feature. */
function handleInput(event) {
  if (event.target.matches('#region-search')) filterRegions(event.target.value);
  if (event.target.matches('#city-search')) filterCities(event.target.value);
}

/** Install application-wide DOM listeners once during bootstrap. */
export function bindAppEvents() {
  document.addEventListener('click', handleClick);
  document.addEventListener('input', handleInput);
  $('#fab')?.addEventListener('click', () => { go('route'); renderRoute(); });
  $('#bottom-nav')?.addEventListener('click', (event) => {
    if (event.target.closest('[data-tab="weather"]') && state.city && state.region) loadWeather();
  });
  window.addEventListener('jarvis:weather', () => loadWeather());
  window.addEventListener('jarvis:language', () => { renderTags(); if (state.weather) renderWeather(); loadRegions(); });
  window.addEventListener('jarvis:favorites-changed', () => loadFavorites());
  bindNavigation();
  initTelegramBackButton();
  installExtraNavigation();
}

/** Bind the feature event graph without exposing individual handlers to the entrypoint. */
export { updateFab };
