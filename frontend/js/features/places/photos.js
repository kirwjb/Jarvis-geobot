import { request } from '../../core/api.js?v=20261017-010';
import { $, esc } from '../../ui/helpers.js?v=20261017-010';
import { t } from '../../ui/language.js?v=20261017-010';
import { placesState } from './state.js?v=20261017-010';
import { ICONS } from '../../ui/icons.js?v=20261017-010';

if (typeof window !== 'undefined') {
  window.__jarvisImgFallback = (img, rawFallback) => {
    if (rawFallback && !img.dataset.triedFallback) {
      img.dataset.triedFallback = '1';
      img.src = rawFallback;
    } else {
      img.onerror = null;
      if (img.parentElement) {
        img.parentElement.innerHTML = `<div class="poi-placeholder">${ICONS.placeholderBuilding}</div>`;
      }
    }
  };
}

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

export function proxyPhotoUrl(rawUrl) {
  const url = resolvePhotoUrl(rawUrl);
  if (!url) return null;
  if (url.includes('wikimedia.org')) {
    return `/api/geo/photo-proxy?url=${encodeURIComponent(url)}`;
  }
  return url;
}

export function photoUrl(data, preferHighRes = false) {
  let raw = null;
  if (preferHighRes) {
    raw =
      data?.photo?.medium_url ||
      data?.images?.medium ||
      data?.photo?.original_url ||
      data?.images?.original ||
      data?.image_url ||
      data?.photo?.thumbnail_url ||
      data?.images?.thumb ||
      null;
  } else {
    raw =
      data?.photo?.thumbnail_url ||
      data?.images?.thumb ||
      data?.image_url ||
      data?.photo?.medium_url ||
      data?.images?.medium ||
      data?.photo?.original_url ||
      data?.images?.original ||
      null;
  }
  return resolvePhotoUrl(raw);
}

export function detailPhotoUrl(data) {
  return photoUrl(data, true);
}

export function renderImageTag(src, alt = '', className = '') {
  const resolved = resolvePhotoUrl(src);
  if (!resolved) {
    return `<div class="poi-placeholder">${ICONS.placeholderBuilding}</div>`;
  }

  const displayUrl = proxyPhotoUrl(resolved);
  const escapedSrc = esc(displayUrl);
  const escapedAlt = esc(alt || t('place') || 'Место');
  const classAttr = className ? `class="${esc(className)}"` : '';

  const isProxied = displayUrl.startsWith('/api/geo/photo-proxy?url=');
  const rawFallback = isProxied ? esc(resolved) : '';
  const fallbackHandler = `onerror="__jarvisImgFallback(this, '${rawFallback}')"`;

  const isDetail = className && className.includes('jarvis-detail-image');
  const loadingAttr = isDetail
    ? 'loading="eager" fetchpriority="high" decoding="sync"'
    : 'loading="lazy" decoding="async"';

  return `<img ${classAttr} src="${escapedSrc}" alt="${escapedAlt}" ${loadingAttr} ${fallbackHandler}>`;
}

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

  } finally {
    placesState.photoLoading.delete(id);
  }
}
