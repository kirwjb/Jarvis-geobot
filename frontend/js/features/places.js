import { state, persist, telegramUserId } from '../core/state.js';
import { request } from '../core/api.js';
import { $, esc, toast, haptic } from '../ui/helpers.js';
import { go } from '../core/router.js';
import { t } from '../ui/language.js';
import { placesState, resetPlacesState, buildPlacesQueryKey } from './places/state.js';
import { loadPage } from './places/pagination.js';
import { poiCardMarkup, renderPlaces, updateRouteFab } from './places/view.js';
import { loadMissingPhotos, photoUrl } from './places/photos.js';

/** Start a fresh POI feed for the selected city and categories. */
export async function loadPlaces() {
  go('cards');
  resetPlacesState();
  placesState.queryKey = buildPlacesQueryKey(state);
  state.pois = [];
  const title = $('#cards-title');
  if (title) title.textContent = state.city || t('places');
  renderPlaces();
  await loadPage(0);
}

/** Toggle the authenticated user's favorite state for a POI. */
export async function toggleFavorite(id) {
  if (!telegramUserId()) return toast(t('tg_only'));
  try {
    const data = await request('/favorites/toggle', { method: 'POST', body: JSON.stringify({ poi_id: String(id) }) });
    data?.favorited ? state.favs.add(String(id)) : state.favs.delete(String(id));
    renderPlaces();
    persist();
    haptic();
    window.dispatchEvent(new CustomEvent('jarvis:favorites-changed'));
  } catch (error) {
    toast(`Не удалось изменить избранное: ${error.message}`);
  }
}

/** Add or remove a POI from the current route and persist the selection. */
export function toggleRoute(id) {
  const key = String(id);
  const exists = state.route.some((item) => String(item.id) === key);
  if (exists) state.route = state.route.filter((item) => String(item.id) !== key);
  else {
    const place = state.pois.find((item) => String(item.id) === key);
    if (place) state.route.push(place);
  }
  updateRouteFab();
  renderPlaces();
  persist();
  haptic();
}

/** Open the independent POI detail endpoint in a modal. */
export async function openDetail(id) {
  try {
    const data = await request(`/geo/pois/${encodeURIComponent(id)}/wikimedia-detail`);
    const image = photoUrl(data);
    const modal = document.createElement('div');
    modal.className = 'jarvis-modal';
    modal.innerHTML = `<div class="jarvis-modal-card"><button class="jarvis-close" type="button" data-action="close-modal">×</button>${image ? `<img class="jarvis-detail-image" src="${esc(image)}" alt="${esc(data.name || '')}" decoding="async">` : '<div class="poi-placeholder">🏛️</div>'}<h2>${esc(data.name || t('place'))}</h2><p>📍 ${esc(data.city || '')}${data.address ? `<br>🏠 ${esc(data.address)}` : ''}</p><div class="jarvis-modal-actions"><button class="btn-main" type="button" data-action="favorite" data-id="${esc(String(data.id))}">♡ ${esc(t('favorite'))}</button><button class="btn-route" type="button" data-action="route" data-id="${esc(String(data.id))}">＋ ${esc(t('route_add'))}</button></div></div>`;
    modal.addEventListener('click', (event) => { if (event.target === modal) modal.remove(); });
    document.body.appendChild(modal);
  } catch (error) {
    toast(`Не удалось загрузить место: ${error.message}`);
  }
}

/** Load the current user's favorite IDs into global application state. */
export async function loadFavorites() {
  if (!telegramUserId()) return;
  try {
    const data = await request('/favorites/me');
    state.favs = new Set((data?.favorites || []).map((item) => String(item.place_id)));
    persist();
  } catch (error) {
    console.warn('favorites', error);
  }
}

export function updateFab() {
  updateRouteFab();
}

export { loadPage, poiCardMarkup, renderPlaces, loadMissingPhotos, updateRouteFab };
