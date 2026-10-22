import { state } from '../../core/state.js?v=20261017-010';
import { $, esc } from '../../ui/helpers.js?v=20261017-010';
import { t, currentLanguage } from '../../ui/language.js?v=20261017-010';
import { placesState } from './state.js?v=20261017-010';
import { renderImageTag } from './photos.js?v=20261017-010';
import { ICONS } from '../../ui/icons.js?v=20261017-010';
import { updateRouteFab } from '../route.js?v=20261017-010';

export { updateRouteFab };

export function getCategoryMeta(category) {
  if (!category) return { icon: ICONS.pin, label: currentLanguage === 'BY' ? 'Славутасць' : 'Достопримечательность' };
  const cat = String(category).toLowerCase().trim();
  if (cat.includes('музе') || cat === 'museum') return { icon: ICONS.museum, label: t('museum') || 'Музей' };
  if (cat.includes('зам') || cat === 'castle') return { icon: ICONS.castle, label: t('castle') || 'Замок' };
  if (cat.includes('парк') || cat === 'park') return { icon: ICONS.park, label: t('park') || 'Парк' };
  if (cat.includes('прырод') || cat.includes('природ') || cat === 'nature') return { icon: ICONS.nature, label: t('nature') || 'Природа' };
  if (cat.includes('храм') || cat.includes('царк') || cat.includes('косц') || cat === 'church') return { icon: ICONS.church, label: t('church') || 'Храм' };
  if (cat.includes('архіт') || cat.includes('архит') || cat === 'architecture') return { icon: ICONS.architecture, label: t('architecture') || 'Архитектура' };
  if (cat.includes('помнік') || cat.includes('памят') || cat === 'monument') return { icon: ICONS.monument, label: t('monument') || 'Памятник' };
  return { icon: ICONS.pin, label: t(category) || category };
}

export function poiCardMarkup(place) {
  const id = String(place.id);
  const image = place.images?.medium || place.images?.thumb || place.image_url;
  const favorite = state.favs.has(id);
  const inRoute = state.route.some((item) => String(item.id) === id);
  const imageMarkup = renderImageTag(image, place.name || t('place'), 'poi-image');
  const catMeta = getCategoryMeta(place.category);
  const routeBtnContent = inRoute
    ? `${ICONS.check} <span>${currentLanguage === 'BY' ? 'Дададзена' : 'Добавлено'}</span>`
    : `${ICONS.plus} <span>${currentLanguage === 'BY' ? 'У маршрут' : 'В маршрут'}</span>`;

  const heartSvg = favorite ? ICONS.heartFilled : ICONS.heartOutline;

  return `<article class="poi-card" data-action="detail" data-id="${esc(id)}">
    <div class="poi-img-wrapper">
      <div class="poi-img">${imageMarkup}</div>
      <div class="poi-overlay-bar">
        <div class="poi-category-chip">
          <span>${catMeta.icon}</span>
          <span>${esc(catMeta.label)}</span>
        </div>
        <button class="poi-fav-btn ${favorite ? 'active' : ''}" type="button" data-action="favorite" data-id="${esc(id)}" aria-label="${favorite ? 'Выдаліць з выбранага' : 'Дадаць у выбранае'}" aria-pressed="${favorite}">
          ${heartSvg}
        </button>
      </div>
    </div>
    <div class="poi-content">
      <div class="poi-info">
        <div class="poi-name">${esc(place.name || t('place'))}</div>
        <div class="poi-loc">${ICONS.pin} <span class="poi-loc-text">${esc(place.city || '')}${place.address ? ` · ${esc(place.address)}` : ''}</span></div>
      </div>
      <button class="route-toggle-btn ${inRoute ? 'in-route' : ''}" type="button" data-action="route" data-id="${esc(id)}" aria-pressed="${inRoute}" aria-label="${inRoute ? 'Выдаліць з маршруту' : 'Дадаць у маршрут'}">
        ${routeBtnContent}
      </button>
    </div>
  </article>`;
}

export function renderPlaces() {
  const feed = $('#feed');
  if (!feed) return;
  if (placesState.loading) {
    feed.innerHTML = `<div class="jarvis-loading"><div class="jarvis-spinner"></div><div class="jarvis-loading-title">${esc(t('searching'))}</div></div>`;
  } else {
    const endBox = (!placesState.hasNext && state.city)
      ? `<div class="places-research-box">
           <p class="places-research-text">${esc(t('research_all_seen'))}</p>
           <button class="btn btn-secondary research-expand-btn" type="button" data-action="research-expand">
             <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/><path d="M11 8v6"/><path d="M8 11h6"/></svg>
             <span>${esc(t('research_expand'))}</span>
           </button>
         </div>`
      : '';
    feed.innerHTML = (state.pois.length ? state.pois.map(poiCardMarkup).join('') : `<div class="empty">${esc(t('nothing'))}</div>`) + endBox;
  }
  const pagination = $('#poi-pagination');
  if (pagination) pagination.innerHTML = (state.pois.length || placesState.hasNext) ? `<button class="poi-page-btn" type="button" data-action="page-prev" data-page="${placesState.page - 1}" ${placesState.page === 0 || placesState.loading ? 'disabled' : ''}>${ICONS.chevronLeft}</button><span class="poi-page-label">${esc(t('page'))} ${placesState.page + 1}</span><button class="poi-page-btn" type="button" data-action="page-next" data-page="${placesState.page + 1}" ${!placesState.hasNext || placesState.loading ? 'disabled' : ''}>${ICONS.chevronRight}</button>` : '';
}
