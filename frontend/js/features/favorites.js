import { state, persist, telegramUserId } from '../core/state.js?v=1791475344';
import { request } from '../core/api.js?v=1791475344';
import { $, esc, toast, haptic } from '../ui/helpers.js?v=1791475344';
import { t } from '../ui/language.js?v=1791475344';
import { poiCardMarkup } from './places/view.js?v=1791475344';

export const favState = {
  page: 0,
  pageSize: 8,
  total: 0,
  pages: 1,
  hasNext: false,
  loading: false,
};

/** Render page pagination controls for favorites. */
export function renderFavPagination() {
  const pagination = $('#fav-pagination');
  if (!pagination) return;
  if (favState.pages <= 1 && favState.total <= favState.pageSize) {
    pagination.innerHTML = '';
    return;
  }
  pagination.innerHTML = `
    <button class="poi-page-btn" type="button" data-action="fav-page-prev" data-page="${favState.page - 1}" ${favState.page === 0 || favState.loading ? 'disabled' : ''}>←</button>
    <span class="poi-page-label">${esc(t('page'))} ${favState.page + 1} / ${Math.max(1, favState.pages)}</span>
    <button class="poi-page-btn" type="button" data-action="fav-page-next" data-page="${favState.page + 1}" ${!favState.hasNext || favState.loading ? 'disabled' : ''}>→</button>
  `;
}

/** Load the authenticated user's favorites with page-based pagination and render them. */
export async function loadFavoritesScreen(page = 0) {
  const box = $('#favorites-list');
  const pagination = $('#fav-pagination');
  if (!box) return;
  if (!telegramUserId()) {
    box.innerHTML = `<div class="empty">${esc(t('tg_only'))}</div>`;
    if (pagination) pagination.innerHTML = '';
    return;
  }

  favState.loading = true;
  favState.page = Math.max(0, page);
  box.innerHTML = `<div class="jarvis-loading"><div class="jarvis-spinner"></div><div class="jarvis-loading-title">${esc(t('loading'))}</div></div>`;
  if (pagination) pagination.innerHTML = '';

  try {
    const data = await request(`/favorites/me?page=${favState.page}&page_size=${favState.pageSize}`);
    const favorites = data?.favorites || [];
    favState.total = data?.total ?? favorites.length;
    favState.pages = data?.pages ?? Math.max(1, Math.ceil(favState.total / favState.pageSize));
    favState.hasNext = Boolean(data?.has_next);

    if (!favorites.length && favState.page === 0) {
      box.innerHTML = `<div class="empty">${esc(t('fav_empty'))}</div>`;
      if (pagination) pagination.innerHTML = '';
      return;
    }

    if (!favorites.length && favState.page > 0) {
      return loadFavoritesScreen(favState.page - 1);
    }

    const places = await Promise.all(favorites.map(async favorite => {
      try {
        return await request(`/pois/${encodeURIComponent(favorite.place_id)}`);
      } catch (_) {
        return { ...favorite, id: favorite.place_id, name: favorite.place_name || favorite.place_id };
      }
    }));
    state.pois = places.filter(Boolean);
    box.innerHTML = state.pois.map(poiCardMarkup).join('');
    renderFavPagination();
  } catch (error) {
    box.innerHTML = `<div class="empty">${esc(error.message || t('places_failed'))}</div>`;
    if (pagination) pagination.innerHTML = '';
    toast(error.message || t('places_failed'));
  } finally {
    favState.loading = false;
  }
}

/** Toggle favorite state for a place with backend sync and event dispatch. */
export async function toggleFavorite(id) {
  if (!telegramUserId()) return toast(t('tg_only'));
  const pid = String(id);
  try {
    const data = await request('/favorites/toggle', { method: 'POST', body: JSON.stringify({ poi_id: pid }) });
    data?.favorited ? state.favs.add(pid) : state.favs.delete(pid);
    persist();
    haptic();
    window.dispatchEvent(new CustomEvent('jarvis:favorites-changed', { detail: { id: pid, favorited: data?.favorited } }));
  } catch (error) {
    toast(`Не удалось изменить избранное: ${error.message}`);
  }
}

/** Load all favorite IDs for the current user to mark hearts across the application. */
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
