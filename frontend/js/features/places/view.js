import { state } from '../../core/state.js';
import { $, esc } from '../../ui/helpers.js';
import { t } from '../../ui/language.js';
import { placesState } from './state.js';

/** Build one POI card; this module contains presentation only. */
export function poiCardMarkup(place) {
  const id = String(place.id);
  const image = place.images?.medium || place.images?.thumb || place.image_url;
  const favorite = state.favs.has(id);
  const inRoute = state.route.some((item) => String(item.id) === id);
  return `<article class="poi-card" data-action="detail" data-id="${esc(id)}"><div class="poi-img">${image ? `<img src="${esc(image)}" alt="${esc(place.name)}" loading="lazy" decoding="async">` : '<div class="poi-placeholder">🏛️</div>'}</div><div class="poi-body"><div class="poi-name">${esc(place.name || t('place'))}</div><div class="poi-loc">📍 ${esc(place.city || '')}${place.address ? ` · ${esc(place.address)}` : ''}</div><div class="poi-actions"><button class="poi-act ${favorite ? 'active' : ''}" type="button" data-action="favorite" data-id="${esc(id)}">${favorite ? '❤️' : '♡'} ${esc(t('favorite'))}</button><button class="poi-act ${inRoute ? 'active' : ''}" type="button" data-action="route" data-id="${esc(id)}">${inRoute ? '✓' : '＋'} ${esc(t('route_add'))}</button></div></div></article>`;
}

/** Render the current places list and pagination controls from feature state. */
export function renderPlaces() {
  const feed = $('#feed');
  if (!feed) return;
  feed.innerHTML = placesState.loading ? `<div class="jarvis-loading"><div class="jarvis-spinner"></div><div class="jarvis-loading-title">${esc(t('searching'))}</div></div>` : state.pois.length ? state.pois.map(poiCardMarkup).join('') : `<div class="empty">${esc(t('nothing'))}</div>`;
  const pagination = $('#poi-pagination');
  if (pagination) pagination.innerHTML = (state.pois.length || placesState.hasNext) ? `<button class="poi-page-btn" type="button" data-action="page-prev" data-page="${placesState.page - 1}" ${placesState.page === 0 || placesState.loading ? 'disabled' : ''}>←</button><span class="poi-page-label">${esc(t('page'))} ${placesState.page + 1}</span><button class="poi-page-btn" type="button" data-action="page-next" data-page="${placesState.page + 1}" ${!placesState.hasNext || placesState.loading ? 'disabled' : ''}>→</button>` : '';
}

/** Update the floating route button without knowing how routes are stored or fetched. */
export function updateRouteFab() {
  const fab = $('#fab');
  if (!fab) return;
  fab.classList.toggle('hidden', !state.route.length);
  const count = $('#fab-count');
  if (count) count.textContent = state.route.length;
}
