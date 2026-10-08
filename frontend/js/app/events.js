import { state } from '../core/state.js?v=1791475344';
import { $, haptic } from '../ui/helpers.js?v=1791475344';
import { toggleTheme } from '../ui/theme.js?v=1791475344';
import { toggleLanguage } from '../ui/language.js?v=1791475344';
import { go, initTelegramBackButton, setTab } from '../core/router.js?v=1791475344';
import { loadRegions, pickRegion, pickCity, toggleTag, filterRegions, filterCities, renderTags, startPlaces } from '../features/travel.js?v=1791475344';
import { loadWeather } from '../features/weather.js?v=1791475344';
import { loadPlaces, openDetail, loadPage, filterPlacesSearch, shufflePlaces, renderPlaces } from '../features/places.js?v=1791475344';
import { loadFavorites, toggleFavorite, loadFavoritesScreen, favState } from '../features/favorites.js?v=1791475344';
import { toggleRoute, updateFab, renderRoute, removeRoute, buildRoute, copyRoute, openRoute } from '../features/route.js?v=1791475344';

let appEventsBound = false;

/** Dispatch a delegated click to the feature that owns the requested action. */
function handleClick(event) {
  const element = event.target.closest('[data-action]');
  if (!element || !document.body.contains(element)) return;
  if (element.closest('.bottom-nav-item')) return;
  const action = element.dataset.action;
  if (action === 'theme') { event.preventDefault(); toggleTheme(); return; }
  if (action === 'language') { event.preventDefault(); toggleLanguage(); return; }
  if (action === 'start') { event.preventDefault(); haptic('medium'); go('regions'); loadRegions(); return; }
  if (action === 'back') { event.preventDefault(); haptic('light'); go(element.dataset.screen || 'regions'); return; }
  if (action === 'region') { event.preventDefault(); haptic('selection'); pickRegion(element.dataset.id); return; }
  if (action === 'city') { event.preventDefault(); haptic('selection'); pickCity(element.dataset.city); return; }
  if (action === 'tag') { event.preventDefault(); haptic('selection'); toggleTag(element.dataset.id); return; }
  if (action === 'show-places') { event.preventDefault(); haptic('medium'); startPlaces(); return; }
  if (action === 'choose-city') { event.preventDefault(); haptic('light'); state.mode = 'weather'; go('regions'); return; }
  if (action === 'weather-refresh') { event.preventDefault(); haptic('light'); loadWeather(); return; }
  if (action === 'page-prev' || action === 'page-next') { event.preventDefault(); haptic('selection'); loadPage(Number(element.dataset.page)); return; }
  if (action === 'fav-page-prev' || action === 'fav-page-next') { event.preventDefault(); haptic('selection'); loadFavoritesScreen(Number(element.dataset.page)); return; }
  if (action === 'shuffle-places') { event.preventDefault(); haptic('medium'); shufflePlaces(); return; }
  if (action === 'favorite') { event.preventDefault(); event.stopPropagation(); toggleFavorite(element.dataset.id); return; }
  if (action === 'route') { event.preventDefault(); event.stopPropagation(); toggleRoute(element.dataset.id); return; }
  if (action === 'detail') { event.preventDefault(); haptic('light'); openDetail(element.dataset.id); return; }
  if (action === 'remove-route') { event.preventDefault(); haptic('medium'); removeRoute(element.dataset.id); return; }
  if (action === 'build-route') { event.preventDefault(); haptic('medium'); buildRoute(); return; }
  if (action === 'open-route') { event.preventDefault(); haptic('light'); openRoute(element.dataset.url); return; }
  if (action === 'copy-route') { event.preventDefault(); haptic('success'); copyRoute(element.dataset.url); return; }
  if (action === 'close-modal') { event.preventDefault(); haptic('light'); element.closest('.jarvis-modal')?.remove(); return; }
  if (action === 'favorites') { event.preventDefault(); haptic('selection'); setTab('favorites'); go('favorites'); loadFavoritesScreen(); return; }
}

/** Route search input changes to the respective features without creating feature-specific listeners. */
function handleInput(event) {
  if (event.target.matches('#region-search')) filterRegions(event.target.value);
  if (event.target.matches('#city-search')) filterCities(event.target.value);
  if (event.target.matches('#poi-search')) filterPlacesSearch(event.target.value);
}

/** Install the single application-wide event delegation layer during bootstrap. */
export function bindAppEvents() {
  if (appEventsBound) return;
  appEventsBound = true;

  document.addEventListener('click', handleClick);
  document.addEventListener('input', handleInput);

  $('#fab')?.addEventListener('click', () => { haptic('medium'); go('route'); renderRoute(); });
  $('#bottom-nav')?.addEventListener('click', event => {
    const item = event.target.closest('[data-tab]');
    if (!item) return;
    event.preventDefault();
    haptic('selection');
    if (state.screen === 'cards') return;
    const tab = item.dataset.tab;
    if (tab === 'travel') {
      state.mode = 'travel';
      setTab(tab);
      go(state.region && state.city ? 'cards' : 'regions');
      return;
    }
    if (tab === 'weather') { state.mode='weather'; setTab(tab); go(state.city && state.region ? 'weather' : 'regions'); if (state.city && state.region) loadWeather(); return; }
    if (tab === 'favorites') { setTab(tab); go('favorites'); loadFavoritesScreen(); return; }
  });
  window.addEventListener('jarvis:weather', loadWeather);
  window.addEventListener('jarvis:language', () => { renderTags(); loadRegions(); });
  window.addEventListener('jarvis:route-changed', () => { if (state.screen === 'cards') renderPlaces(); });
  window.addEventListener('jarvis:favorites-changed', () => {
    loadFavorites();
    if (state.screen === 'cards') renderPlaces();
    if (state.screen === 'favorites') loadFavoritesScreen(favState.page);
  });
  initTelegramBackButton();
}

/** Expose the floating route button updater to the bootstrap module. */
export { updateFab };
