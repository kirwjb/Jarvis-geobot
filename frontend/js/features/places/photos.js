import { request } from '../../core/api.js';
import { $, esc } from '../../ui/helpers.js';
import { t } from '../../ui/language.js';
import { placesState } from './state.js';

/** Extract the preferred Wikimedia image URL from a photo response. */
export function photoUrl(data) {
  return data?.photo?.thumbnail_url || data?.photo?.original_url || null;
}

/** Load missing Wikimedia URLs without downloading image bytes through our backend. */
export async function loadMissingPhotos(places) {
  const missing = places.filter((place) => place?.id && !place.images?.medium && !place.images?.thumb && !place.image_url && !placesState.photoLoading.has(String(place.id)));
  for (let i = 0; i < missing.length; i += 3) {
    await Promise.all(missing.slice(i, i + 3).map(loadPlacePhoto));
  }
}

/** Resolve one place to a Wikimedia URL and update only its existing card. */
async function loadPlacePhoto(place) {
  const id = String(place.id);
  placesState.photoLoading.add(id);
  try {
    const data = await request(`/geo/pois/${encodeURIComponent(id)}/wikimedia-photo`);
    const image = photoUrl(data);
    if (!image) return;
    Object.assign(place, { image_url: image, images: { thumb: image, medium: image, original: data?.photo?.original_url || image } });
    const media = [...document.querySelectorAll('#feed .poi-card')].find((card) => card.dataset.id === id)?.querySelector('.poi-img');
    if (media) media.innerHTML = `<img src="${esc(image)}" alt="${esc(place.name || t('place'))}" loading="lazy" decoding="async">`;
  } catch (_) {
    // Missing Wikimedia media must not make the POI itself disappear.
  } finally {
    placesState.photoLoading.delete(id);
  }
}
