import { state } from '../core/state.js';
import { $ } from '../ui/helpers.js';
import { toggleTheme } from '../ui/theme.js';
import { toggleLanguage } from '../ui/language.js';
import { go, initTelegramBackButton, bindNavigation, setTab } from '../core/router.js';
import { loadRegions, pickRegion, pickCity, toggleTag, filterRegions, filterCities, renderTags, startPlaces } from '../features/travel.js';
import { loadWeather, renderWeather } from '../features/weather.js';
import { loadFavorites, toggleFavorite, toggleRoute, openDetail, loadPage, updateFab } from '../features/places.js';
import { loadFavoritesScreen } from '../features/favorites.js';
import { renderRoute, removeRoute, buildRoute, copyRoute, openRoute } from '../features/route.js';
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
  if (action === 'region') { event.preventDefault(); pickRegion(element.dataset.id); return; }
  if (action === 'city') { event.preventDefault(); pickCity(element.dataset.city); return; }
  if (action === 'tag') { event.preventDefault(); toggleTag(element.dataset.id); return; }
  if (action === 'show-places') { event.preventDefault(); startPlaces(); return; }
  if (action === 'choose-city') { event.preventDefault(); state.mode = 'weather'; go('regions'); return; }
  if (action === 'weather-refresh') { event.preventDefault(); loadWeather(); return; }
  if (action === 'page-prev' || action === 'page-next') { event.preventDefault(); loadPage(Number(element.dataset.page)); return; }
  if (action === 'favorite') { event.preventDefault(); event.stopPropagation(); toggleFavorite(element.dataset.id); return; }
  if (action === 'route') { event.preventDefault(); event.stopPropagation(); toggleRoute(element.dataset.id); return; }
  if (action === 'detail') { event.preventDefault(); openDetail(element.dataset.id); return; }
  if (action === 'remove-route') { event.preventDefault(); removeRoute(element.dataset.id); return; }
  if (action === 'build-route') { event.preventDefault(); buildRoute(); return; }
  if (action === 'open-route') { event.preventDefault(); openRoute(element.dataset.url); return; }
  if (action === 'copy-route') { event.preventDefault(); copyRoute(element.dataset.url); return; }
  if (action === 'close-modal') { event.preventDefault(); element.closest('.jarvis-modal')?.remove(); return; }
  if (action === 'groups') { event.preventDefault(); setTab('groups'); go('groups'); loadGroups(); return; }
  if (action === 'favorites') { event.preventDefault(); setTab('favorites'); go('favorites'); loadFavoritesScreen(); return; }
  if (action === 'group-open') { event.preventDefault(); openGroup(Number(element.dataset.id)); return; }
  if (action === 'group-create') { event.preventDefault(); createGroup(); return; }
  if (action === 'group-invite') { event.preventDefault(); invite(); return; }
  if (action === 'group-send') { event.preventDefault(); send(); return; }
  if (action === 'group-date-save') { event.preventDefault(); saveDate(); return; }
  if (action === 'group-propose') { event.preventDefault(); proposePlace(); return; }
  if (action === 'group-propose-place') { event.preventDefault(); submitProposal(element.dataset.place); return; }
  if (action === 'group-vote') { event.preventDefault(); vote(element.dataset.place); return; }
  if (action === 'group-toggle-voting') { event.preventDefault(); toggleVoting(); }
}

/** Route search input changes to the travel feature without creating feature-specific listeners. */
function handleInput(event) {
  if (event.target.matches('#region-search')) filterRegions(event.target.value);
  if (event.target.matches('#city-search')) filterCities(event.target.value);
}

/** Install the single application-wide event delegation layer during bootstrap. */
export function bindAppEvents() {
  document.addEventListener('click', handleClick);
  document.addEventListener('input', handleInput);
  $('#fab')?.addEventListener('click', () => { go('route'); renderRoute(); });
  $('#bottom-nav')?.addEventListener('click', event => {
    const item = event.target.closest('[data-tab]');
    if (!item) return;
    const tab = item.dataset.tab;
    event.preventDefault();
    if (tab === 'travel') { setTab('travel'); go('splash'); return; }
    if (tab === 'weather') {
      setTab('weather');
      go('weather');
      if (state.city && state.region) loadWeather();
      return;
    }
    if (tab === 'favorites') {
      setTab('favorites');
      go('favorites');
      loadFavoritesScreen();
      return;
    }
    if (tab === 'groups') {
      setTab('groups');
      go('groups');
      loadGroups();
    }
  });
  window.addEventListener('jarvis:weather', loadWeather);
  window.addEventListener('jarvis:language', () => { renderTags(); loadRegions(); });
  window.addEventListener('jarvis:favorites-changed', () => { loadFavorites(); if (state.screen === 'favorites') loadFavoritesScreen(); });
  bindNavigation();
  initTelegramBackButton();
}

/** Expose the floating route button updater to the bootstrap module. */
export { updateFab };
