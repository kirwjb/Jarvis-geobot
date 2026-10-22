import { state } from '../core/state.js?v=20261017-010';
import { request } from '../core/api.js?v=20261017-010';
import { $, esc, toast } from '../ui/helpers.js?v=20261017-010';
import { go } from '../core/router.js?v=20261017-010';
import { t } from '../ui/language.js?v=20261017-010';
import { placesState, resetPlacesState, buildPlacesQueryKey, generateShuffleSeed } from './places/state.js?v=20261017-010';
import { loadPage } from './places/pagination.js?v=20261017-010';
import { poiCardMarkup, renderPlaces } from './places/view.js?v=20261017-010';
import { loadMissingPhotos, photoUrl, detailPhotoUrl, renderImageTag } from './places/photos.js?v=20261017-010';
import { toggleFavorite, loadFavorites } from './favorites.js?v=20261017-010';
import { toggleRoute, updateRouteFab, updateFab } from './route.js?v=20261017-010';
import { ICONS } from '../ui/icons.js?v=20261017-010';

let searchDebounceTimer = null;

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

export function shufflePlaces() {
  placesState.shuffleSeed = generateShuffleSeed();
  placesState.cache.clear();
  placesState.queryKey = buildPlacesQueryKey(state);
  loadPage(0);
}

export async function openDetail(id) {
  try {
    const data = await request(`/geo/pois/${encodeURIComponent(id)}/wikimedia-detail`);
    const placeId = String(data?.id || id);
    const image = detailPhotoUrl(data) || data?.images?.medium || data?.photo?.medium_url || photoUrl(data);
    const modal = document.createElement('div');
    modal.className = 'jarvis-modal';
    const imageMarkup = renderImageTag(image, data.name || '', 'jarvis-detail-image');
    const hasPhoto = Boolean(image);
    const overlayActionsMarkup = hasPhoto ? `
      <div class="jarvis-photo-overlay-actions">
        <button class="jarvis-photo-overlay-btn btn-report-photo" type="button" data-action="report-photo" data-id="${esc(placeId)}" title="${esc(t('report_photo'))}" aria-label="${esc(t('report_photo'))}">
          ${ICONS.flag}
          <span>${esc(t('report_photo'))}</span>
        </button>
        <button class="jarvis-photo-overlay-btn btn-delete-photo" type="button" data-action="delete-photo" data-id="${esc(placeId)}" title="${esc(t('delete_photo'))}" aria-label="${esc(t('delete_photo'))}">
          ${ICONS.trash}
          <span>${esc(t('delete_photo'))}</span>
        </button>
      </div>` : '';
    const photoSectionMarkup = `<div class="jarvis-detail-photo-wrapper">${imageMarkup}${overlayActionsMarkup}</div>`;

    modal.innerHTML = `<div class="jarvis-modal-card"><button class="jarvis-close" type="button" data-action="close-modal" aria-label="${esc(t('close') || 'Закрыць')}">${ICONS.close}</button>${photoSectionMarkup}<h2>${esc(data.name || t('place'))}</h2><p class="poi-detail-loc">${ICONS.pin} <span>${esc(data.city || '')}</span>${data.address ? `<br>${ICONS.house} <span>${esc(data.address)}</span>` : ''}</p><div class="jarvis-modal-actions"><button class="btn-main" type="button" data-action="favorite" data-id="${esc(placeId)}">${ICONS.heartOutline} <span>${esc(t('favorite'))}</span></button><button class="btn-route" type="button" data-action="route" data-id="${esc(placeId)}">${ICONS.plus} <span>${esc(t('route_add'))}</span></button></div></div>`;
    modal.addEventListener('click', (event) => { if (event.target === modal) modal.remove(); });
    document.body.appendChild(modal);
  } catch (error) {
    toast(`Не удалось загрузить место: ${error.message}`);
  }
}

export async function reportPhoto(id) {
  const reason = window.prompt(
    t('report_prompt'),
    t('report_default_reason')
  );
  if (reason === null) return;
  try {
    const res = await request(`/geo/pois/${encodeURIComponent(id)}/report-photo`, {
      method: 'POST',
      body: JSON.stringify({ reason: reason.trim() || 'inappropriate' }),
    });
    toast(res?.message || t('report_sent'));
  } catch (err) {
    toast(`${t('report_error')} ${err.message}`);
  }
}

export async function deletePhoto(id, modal) {
  if (!window.confirm(t('delete_photo_confirm'))) return;
  try {
    const res = await request(`/geo/pois/${encodeURIComponent(id)}/block-photo`, {
      method: 'POST',
      body: JSON.stringify({ reason: 'user_delete' }),
    });
    toast(res?.message || t('photo_deleted'));

    if (modal) {
      const wrapper = modal.querySelector('.jarvis-detail-photo-wrapper');
      if (wrapper) {
        wrapper.innerHTML = `<div class="poi-placeholder">${ICONS.placeholderBuilding}</div>`;
      }
    }

    if (Array.isArray(state.pois)) {
      const item = state.pois.find((p) => String(p.id) === String(id));
      if (item) {
        item.photo = null;
        item.image_url = null;
        item.images = null;
      }
    }

    if (placesState.cache) {
      for (const cachedPage of placesState.cache.values()) {
        if (Array.isArray(cachedPage?.places)) {
          for (const p of cachedPage.places) {
            if (String(p.id) === String(id)) {
              p.photo = null;
              p.image_url = null;
              p.images = null;
            }
          }
        }
      }
    }

    const cards = document.querySelectorAll('.poi-card');
    for (const card of cards) {
      if (card.dataset.id === String(id)) {
        const media = card.querySelector('.poi-img');
        if (media) {
          media.innerHTML = `<div class="poi-placeholder">${ICONS.placeholderBuilding}</div>`;
        }
      }
    }
  } catch (err) {
    toast(`${t('delete_error')} ${err.message}`);
  }
}

async function researchSurroundings() {
  if (!state.city || placesState.loading) return;
  placesState.loading = true;
  renderPlaces();
  toast(t('research_searching'));
  try {
    const res = await request('/pois/research', {
      method: 'POST',
      body: JSON.stringify({
        city: state.city,
        region: state.region || null,
        scale: 2.5
      })
    });
    if (res?.new_added > 0) {
      toast(`${t('research_found')}${res.new_added}`);

      placesState.cache.clear();
      placesState.queryKey = buildPlacesQueryKey(state);
      await loadPage(placesState.page);
    } else {
      toast(t('research_none'));
    }
  } catch (err) {
    toast(`Ошибка поиска: ${err.message}`);
  } finally {
    placesState.loading = false;
    renderPlaces();
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
  researchSurroundings,
};
