import { state, telegramUserId } from '../core/state.js';
import { request } from '../core/api.js';
import { $, esc, toast } from '../ui/helpers.js';
import { t } from '../ui/language.js';
import { poiCardMarkup } from './places.js';

/** Load the authenticated user's favorites and render them into the favorites screen. */
export async function loadFavoritesScreen() {
  const box = $('#favorites-list');
  if (!box) return;
  if (!telegramUserId()) {
    box.innerHTML = `<div class="empty">${esc(t('tg_only'))}</div>`;
    return;
  }

  box.innerHTML = `<div class="jarvis-loading"><div class="jarvis-spinner"></div><div class="jarvis-loading-title">${esc(t('loading'))}</div></div>`;
  try {
    const data = await request('/favorites/me');
    const favorites = data?.favorites || [];
    if (!favorites.length) {
      box.innerHTML = `<div class="empty">${esc(t('fav_empty'))}</div>`;
      return;
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
  } catch (error) {
    box.innerHTML = `<div class="empty">${esc(error.message || t('places_failed'))}</div>`;
    toast(error.message || t('places_failed'));
  }
}
