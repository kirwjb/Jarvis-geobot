import { state } from '../core/state.js?v=1791475344';
import { request } from '../core/api.js?v=1791475344';
import { $, esc, toast } from '../ui/helpers.js?v=1791475344';
import { go } from '../core/router.js?v=1791475344';
import { t } from '../ui/language.js?v=1791475344';
import { placesState, resetPlacesState, buildPlacesQueryKey, generateShuffleSeed } from './places/state.js?v=1791475344';
import { loadPage } from './places/pagination.js?v=1791475344';
import { poiCardMarkup, renderPlaces } from './places/view.js?v=1791475344';
import { loadMissingPhotos, photoUrl, renderImageTag } from './places/photos.js?v=1791475344';
import { toggleFavorite, loadFavorites } from './favorites.js?v=1791475344';
import { toggleRoute, updateRouteFab, updateFab } from './route.js?v=1791475344';

let searchDebounceTimer = null;

/** Start a fresh POI feed with session-consistent random ordering. */
export async function loadPlaces() {
  go('cards');
  resetPlacesState();
  placesState.shuffleSeed = generateShuffleSeed();
  placesState.queryKey = buildPlacesQueryKey(state);
  state.pois = [];
  const title = $('#cards-title');
  if (title) title.textContent = state.city || t('places');
  const searchInput = $('#poi-search');
  if (searchInput) searchInput.value = '';
  renderPlaces();
  await loadPage(0);
}

/** Filter places by text query with debouncing across backend database points. */
export function filterPlacesSearch(term) {
  clearTimeout(searchDebounceTimer);
  searchDebounceTimer = setTimeout(() => {
    const query = (term || '').trim();
    if (placesState.search === query) return;
    placesState.search = query;
    placesState.cache.clear();
    placesState.queryKey = buildPlacesQueryKey(state);
    loadPage(0);
  }, 250);
}

/** Trigger a fresh backend-driven random ordering using a new shuffle seed. */
export function shufflePlaces() {
  placesState.shuffleSeed = generateShuffleSeed();
  placesState.cache.clear();
  placesState.queryKey = buildPlacesQueryKey(state);
  loadPage(0);
}

/** Open the independent POI detail endpoint in a modal. */
export async function openDetail(id) {
  try {
    const data = await request(`/geo/pois/${encodeURIComponent(id)}/wikimedia-detail`);
    const image = photoUrl(data);
    const modal = document.createElement('div');
    modal.className = 'jarvis-modal';
    const imageMarkup = renderImageTag(image, data.name || '', 'jarvis-detail-image');
    modal.innerHTML = `<div class="jarvis-modal-card"><button class="jarvis-close" type="button" data-action="close-modal">×</button>${imageMarkup}<h2>${esc(data.name || t('place'))}</h2><p>📍 ${esc(data.city || '')}${data.address ? `<br>🏠 ${esc(data.address)}` : ''}</p><div class="jarvis-modal-actions"><button class="btn-main" type="button" data-action="favorite" data-id="${esc(String(data.id))}">♡ ${esc(t('favorite'))}</button><button class="btn-route" type="button" data-action="route" data-id="${esc(String(data.id))}">＋ ${esc(t('route_add'))}</button></div></div>`;
    modal.addEventListener('click', (event) => { if (event.target === modal) modal.remove(); });
    document.body.appendChild(modal);
  } catch (error) {
    toast(`Не удалось загрузить место: ${error.message}`);
  }
}

export {
  loadPage,
  poiCardMarkup,
  renderPlaces,
  loadMissingPhotos,
  toggleFavorite,
  loadFavorites,
  toggleRoute,
  updateRouteFab,
  updateFab,
};
