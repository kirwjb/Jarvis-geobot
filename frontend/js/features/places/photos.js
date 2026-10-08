import { request } from '../../core/api.js?v=1791475344';
import { $, esc } from '../../ui/helpers.js?v=1791475344';
import { t } from '../../ui/language.js?v=1791475344';
import { placesState } from './state.js?v=1791475344';

/** Normalize any asset or Wikimedia image URL (stripping local dev hosts, ensuring HTTPS). */
export function resolvePhotoUrl(rawUrl) {
  if (!rawUrl || typeof rawUrl !== 'string') return null;
  let url = rawUrl.trim();
  if (url.startsWith('http://localhost:8000') || url.startsWith('http://127.0.0.1:8000')) {
    url = url.replace(/^http:\/\/(localhost|127\.0\.0\.1):8000/, '');
  }
  if (url.startsWith('http://') && !url.includes('localhost') && !url.includes('127.0.0.1')) {
    url = 'https://' + url.slice(7);
  }
  return url;
}

/** Construct proxy URL for remote Wikimedia images to bypass referer blocks and mixed content. */
export function proxyPhotoUrl(rawUrl) {
  const url = resolvePhotoUrl(rawUrl);
  if (!url) return null;
  if (url.includes('wikimedia.org')) {
    return `/api/geo/photo-proxy?url=${encodeURIComponent(url)}`;
  }
  return url;
}

/** Extract the preferred image URL from an API photo response. */
export function photoUrl(data) {
  const raw =
    data?.photo?.thumbnail_url ||
    data?.photo?.original_url ||
    data?.image_url ||
    data?.images?.medium ||
    data?.images?.thumb ||
    data?.images?.original ||
    null;
  return resolvePhotoUrl(raw);
}

/**
 * Generate a resilient HTML <img> tag:
 * 1. Automatically uses photo-proxy for remote Wikimedia images to bypass 403 / Referer blocks.
 * 2. Uses local /media/ URLs directly.
 * 3. Gracefully falls back to placeholder icon if image fails to load.
 */
export function renderImageTag(src, alt = '', className = '') {
  const resolved = resolvePhotoUrl(src);
  if (!resolved) {
    return '<div class="poi-placeholder">🏛️</div>';
  }

  const displayUrl = proxyPhotoUrl(resolved);
  const escapedSrc = esc(displayUrl);
  const escapedAlt = esc(alt || t('place') || 'Место');
  const classAttr = className ? `class="${esc(className)}"` : '';

  const isProxied = displayUrl.startsWith('/api/geo/photo-proxy?url=');
  const rawFallback = isProxied ? esc(resolved) : '';
  const fallbackHandler = isProxied
    ? `onerror="if(this.dataset.triedFallback){this.onerror=null;this.parentElement.innerHTML='<div class=\\'poi-placeholder\\'>🏛️</div>';}else{this.dataset.triedFallback='1';this.src='${rawFallback}';}"`
    : `onerror="this.onerror=null;this.parentElement.innerHTML='<div class=\\'poi-placeholder\\'>🏛️</div>';"`;

  return `<img ${classAttr} src="${escapedSrc}" alt="${escapedAlt}" loading="lazy" decoding="async" ${fallbackHandler}>`;
}

/** Load missing Wikimedia URLs without downloading image bytes through our backend. */
export async function loadMissingPhotos(places) {
  const missing = places.filter(
    (place) =>
      place?.id &&
      !place.images?.medium &&
      !place.images?.thumb &&
      !place.image_url &&
      !placesState.photoLoading.has(String(place.id))
  );
  for (let i = 0; i < missing.length; i += 3) {
    await Promise.all(missing.slice(i, i + 3).map(loadPlacePhoto));
  }
}

/** Resolve one place to a photo URL and update its card. */
async function loadPlacePhoto(place) {
  const id = String(place.id);
  placesState.photoLoading.add(id);
  try {
    const data = await request(`/geo/pois/${encodeURIComponent(id)}/wikimedia-photo`);
    const image = photoUrl(data);
    if (!image) return;

    Object.assign(place, {
      image_url: image,
      images: {
        thumb: image,
        medium: image,
        original: resolvePhotoUrl(data?.photo?.original_url) || image,
      },
    });

    const cards = document.querySelectorAll('.poi-card');
    for (const card of cards) {
      if (card.dataset.id === id) {
        const media = card.querySelector('.poi-img');
        if (media) {
          media.innerHTML = renderImageTag(image, place.name || t('place'), 'poi-image');
        }
      }
    }
  } catch (_) {
    // Missing media must not break the POI card display.
  } finally {
    placesState.photoLoading.delete(id);
  }
}
