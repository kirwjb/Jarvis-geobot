import { state, tg } from '../core/state.js?v=20261017-010';
import { $, haptic } from '../ui/helpers.js?v=20261017-010';
import { toggleTheme } from '../ui/theme.js?v=20261017-010';
import { toggleLanguage } from '../ui/language.js?v=20261017-010';
import { go, initTelegramBackButton, setTab } from '../core/router.js?v=20261017-010';
import { loadRegions, pickRegion, pickCity, toggleTag, filterRegions, filterCities, renderTags, startPlaces } from '../features/travel.js?v=20261017-010';
import { loadWeather, selectWeatherCity, filterWeatherCities, closeWeatherDropdown, renderWeatherCityChips } from '../features/weather.js?v=20261017-010';
import { loadPlaces, openDetail, loadPage, filterPlacesSearch, shufflePlaces, renderPlaces, researchSurroundings, reportPhoto, deletePhoto } from '../features/places.js?v=20261017-010';
import { loadFavorites, toggleFavorite, loadFavoritesScreen, favState } from '../features/favorites.js?v=20261017-010';
import { toggleRoute, updateFab, renderRoute, removeRoute, buildRoute, copyRoute, openRoute } from '../features/route.js?v=20261017-010';
import { openLegalModal } from '../features/legal.js?v=20261017-010';

let appEventsBound = false;

function handleTabSwitch(tab) {
  if (tab === 'travel') {
    state.mode = 'travel';
    if (state.region && state.city && state.tags?.size > 0 && state.pois?.length > 0) {
      go('cards');
    } else if (state.region && state.city) {
      renderTags();
      go('tags');
    } else if (state.region) {
      go('cities');
    } else {
      go('regions');
      loadRegions();
    }
    return;
  }
  if (tab === 'route') {
    go('route');
    renderRoute();
    return;
  }
  if (tab === 'weather') {
    state.mode = 'weather';
    go('weather');
    loadWeather();
    return;
  }
  if (tab === 'favorites') {
    go('favorites');
    loadFavoritesScreen();
    return;
  }
}

function handleClick(event) {
  const tabItem = event.target.closest('[data-tab]');
  if (tabItem) {
    event.preventDefault();
    haptic('selection');
    handleTabSwitch(tabItem.dataset.tab);
    return;
  }

  if (!event.target.closest('#weather-city-search') && !event.target.closest('#weather-city-dropdown')) {
    closeWeatherDropdown();
  }

  const element = event.target.closest('[data-action]');
  if (!element || !document.body.contains(element)) return;
  const action = element.dataset.action;
  if (action === 'theme') { event.preventDefault(); toggleTheme(); return; }
  if (action === 'language') { event.preventDefault(); toggleLanguage(); return; }
  if (action === 'legal') { event.preventDefault(); haptic('selection'); openLegalModal(); return; }
  if (action === 'start') { event.preventDefault(); haptic('medium'); go('regions'); loadRegions(); return; }
  if (action === 'back') {
    event.preventDefault();
    haptic('light');
    if (state.screen === 'favorites') {
      go(state.previousScreen && state.previousScreen !== 'favorites' ? state.previousScreen : 'splash');
      return;
    }
    if (state.screen === 'weather') {
      const fallback = (state.region && state.city && state.tags?.size > 0 && state.pois?.length > 0) ? 'cards'
        : (state.region && state.city) ? 'tags'
        : state.region ? 'cities' : 'splash';
      const prev = state.previousScreen && state.previousScreen !== 'weather' ? state.previousScreen : fallback;
      if (prev === 'cards' && (!state.tags?.size || !state.pois?.length)) {
        go(state.region && state.city ? 'tags' : 'regions');
        return;
      }
      go(prev);
      return;
    }
    go(element.dataset.screen || 'regions');
    return;
  }
  if (action === 'region') { event.preventDefault(); haptic('selection'); pickRegion(element.dataset.id); return; }
  if (action === 'city') { event.preventDefault(); haptic('selection'); pickCity(element.dataset.city); return; }
  if (action === 'tag') { event.preventDefault(); haptic('selection'); toggleTag(element.dataset.id); return; }
  if (action === 'show-places') { event.preventDefault(); haptic('medium'); startPlaces(); return; }
  if (action === 'choose-city') { event.preventDefault(); haptic('light'); state.mode = 'weather'; go('regions'); loadRegions(); return; }
  if (action === 'weather-city') { event.preventDefault(); haptic('selection'); selectWeatherCity(element.dataset.city); return; }
  if (action === 'weather-refresh') { event.preventDefault(); haptic('light'); loadWeather(state.weatherCity || state.city || 'Минск'); return; }
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
  if (action === 'research-expand') { event.preventDefault(); haptic('medium'); researchSurroundings(); return; }
  if (action === 'report-photo') { event.preventDefault(); event.stopPropagation(); haptic('medium'); reportPhoto(element.dataset.id); return; }
  if (action === 'delete-photo' || action === 'block-photo') { event.preventDefault(); event.stopPropagation(); haptic('heavy'); deletePhoto(element.dataset.id, element.closest('.jarvis-modal')); return; }
}

function handleInput(event) {
  if (event.target.matches('#region-search')) filterRegions(event.target.value);
  if (event.target.matches('#city-search')) filterCities(event.target.value);
  if (event.target.matches('#poi-search')) filterPlacesSearch(event.target.value);
  if (event.target.matches('#weather-city-search')) filterWeatherCities(event.target.value);
}

function handleKeydown(event) {
  if (event.target.matches('#weather-city-search')) {
    if (event.key === 'Enter') {
      event.preventDefault();
      const firstOption = document.querySelector('#weather-city-dropdown .weather-city-option');
      if (firstOption && firstOption.dataset.city) {
        selectWeatherCity(firstOption.dataset.city);
      } else if (event.target.value.trim()) {
        selectWeatherCity(event.target.value.trim());
      }
    } else if (event.key === 'Escape') {
      closeWeatherDropdown();
    }
  }
}

export function bindAppEvents() {
  if (appEventsBound) return;
  appEventsBound = true;

  document.addEventListener('click', handleClick);
  document.addEventListener('input', handleInput);
  document.addEventListener('keydown', handleKeydown);

  try {
    tg?.MainButton?.hide?.();
  } catch (_) {}
  window.addEventListener('jarvis:weather', (event) => {
    const city = event?.detail?.city || state.weatherCity || state.city || 'Минск';
    loadWeather(city);
  });
  window.addEventListener('jarvis:language', () => {
    renderTags();
    loadRegions();
    renderWeatherCityChips();
  });
  window.addEventListener('jarvis:route-changed', () => { if (state.screen === 'cards') renderPlaces(); });
  window.addEventListener('jarvis:favorites-changed', () => {
    loadFavorites();
    if (state.screen === 'cards') renderPlaces();
    if (state.screen === 'favorites') loadFavoritesScreen(favState.page);
  });
  initTelegramBackButton();
}

export { updateFab };
