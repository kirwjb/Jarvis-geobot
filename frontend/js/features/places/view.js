import { state } from '../../core/state.js?v=1791475344';
import { $, esc } from '../../ui/helpers.js?v=1791475344';
import { t } from '../../ui/language.js?v=1791475344';
import { placesState } from './state.js?v=1791475344';
import { renderImageTag } from './photos.js?v=1791475344';

/** Build one POI card with resilient photo rendering and fallbacks. */
export function poiCardMarkup(place) {
  const id = String(place.id);
  const image = place.images?.medium || place.images?.thumb || place.image_url;
  const favorite = state.favs.has(id);
  const inRoute = state.route.some((item) => String(item.id) === id);
  const imageMarkup = renderImageTag(image, place.name || t('place'), 'poi-image');
  return `<article class="poi-card" data-action="detail" data-id="${esc(id)}"><div class="poi-img">${imageMarkup}</div><div class="poi-body"><div class="poi-name">${esc(place.name || t('place'))}</div><div class="poi-loc">📍 ${esc(place.city || '')}${place.address ? ` · ${esc(place.address)}` : ''}</div><div class="poi-actions"><button class="poi-act ${favorite ? 'active' : ''}" type="button" data-action="favorite" data-id="${esc(id)}">${favorite ? '❤️' : '♡'} ${esc(t('favorite'))}</button><button class="poi-act ${inRoute ? 'active' : ''}" type="button" data-action="route" data-id="${esc(id)}">${inRoute ? '✓' : '＋'} ${esc(t('route_add'))}</button></div></div></article>`;
}

/** Render the current places list and pagination controls from feature state. */
export function renderPlaces() {
  const feed = $('#feed');
  if (!feed) return;
  feed.innerHTML = placesState.loading ? `<div class="jarvis-loading"><div class="jarvis-spinner"></div><div class="jarvis-loading-title">${esc(t('searching'))}</div></div>` : state.pois.length ? state.pois.map(poiCardMarkup).join('') : `<div class="empty">${esc(t('nothing'))}</div>`;
  const pagination = $('#poi-pagination');
  if (pagination) pagination.innerHTML = (state.pois.length || placesState.hasNext) ? `<button class="poi-page-btn" type="button" data-action="page-prev" data-page="${placesState.page - 1}" ${placesState.page === 0 || placesState.loading ? 'disabled' : ''}>←</button><span class="poi-page-label">${esc(t('page'))} ${placesState.page + 1}</span><button class="poi-page-btn" type="button" data-action="page-next" data-page="${placesState.page + 1}" ${!placesState.hasNext || placesState.loading ? 'disabled' : ''}>→</button>` : '';
}

import { updateRouteFab } from '../route.js?v=1791475344';
export { updateRouteFab };
