import { state, persist, tg } from '../core/state.js?v=20261017-010';
import { request } from '../core/api.js?v=20261017-010';
import { $, esc, toast, haptic } from '../ui/helpers.js?v=20261017-010';
import { t } from '../ui/language.js?v=20261017-010';
import { ICONS } from '../ui/icons.js?v=20261017-010';

export function updateRouteFab() {
  const badge = $('#route-badge');
  if (badge) {
    const count = state.route.length;
    badge.textContent = String(count);
    badge.style.display = count > 0 ? 'inline-flex' : 'none';
  }
}
export const updateFab = updateRouteFab;

export function toggleRoute(id) {
  const key = String(id);
  const exists = state.route.some((item) => String(item.id) === key);
  if (exists) {
    state.route = state.route.filter((item) => String(item.id) !== key);
  } else {
    const place = state.pois.find((item) => String(item.id) === key);
    if (place) state.route.push(place);
  }
  updateRouteFab();
  persist();
  haptic('selection');
  window.dispatchEvent(new CustomEvent('jarvis:route-changed', { detail: { id: key } }));
}

export function renderRoute() {
  const list = $('#route-list'), btn = $('#btn-build');
  if (!list) return;
  if (!state.route.length) {
    list.innerHTML = `<div class="route-empty">${esc(t('route_empty'))}</div>`;
    if (btn) btn.disabled = true;
    try { tg?.MainButton?.hide?.(); } catch (_) {}
    return;
  }
  const canBuild = state.route.length >= 2;
  if (btn) btn.disabled = !canBuild;
  list.innerHTML = state.route.map((p, i) => `<div class="route-item"><div class="route-num">${i + 1}</div><div class="route-info"><div class="route-name">${esc(p.name)}</div><div class="route-city">${esc(p.city || '')}</div></div><button class="route-del" type="button" data-action="remove-route" data-id="${esc(String(p.id))}" aria-label="Выдаліць">${ICONS.close}</button></div>`).join('');

  try { tg?.MainButton?.hide?.(); } catch (_) {}
}

export function removeRoute(id) {
  state.route = state.route.filter((p) => String(p.id) !== String(id));
  updateRouteFab();
  renderRoute();
  persist();
  window.dispatchEvent(new CustomEvent('jarvis:route-changed', { detail: { id: String(id) } }));
}
export async function buildRoute() {
  if (state.route.length < 2) {
    return toast('Дадайце мінімум 2 пункты');
  }

  const btn = $('#btn-build');
  if (btn) {
    btn.disabled = true;
    btn.textContent = 'Будуем маршрут...';
  }

  try {
    const d = await request('/route/build', {
      method: 'POST',
      body: JSON.stringify({
        poi_ids: state.route.map((p) => String(p.id)),
        optimize: true,
      }),
    });

    const names = state.route.map((p, i) => `${i + 1}. ${p.name}`).join('\n');
    const url = d?.google_maps_url || '';
    const modal = document.createElement('div');
    modal.className = 'jarvis-modal';
    modal.innerHTML = `
      <div class="jarvis-modal-card">
        <button class="jarvis-close" type="button" data-action="close-modal" aria-label="Закрыць">${ICONS.close}</button>
        <h2>${ICONS.map} <span>${esc(t('route_ready'))}</span></h2>
        <p class="jarvis-route-text">${esc(names)}</p>
        ${d?.total_distance_km != null ? `<p>${esc(t('distance'))}: ${esc(String(d.total_distance_km))} км</p>` : ''}
        <p class="jarvis-route-url">${esc(url)}</p>
        <button class="btn-main" type="button" data-action="open-route" data-url="${esc(url)}">${esc(t('open_maps'))}</button>
        <button class="btn-route" type="button" data-action="copy-route" data-url="${esc(url)}">${esc(t('copy'))}</button>
      </div>`;

    modal.addEventListener('click', (e) => {
      if (e.target === modal) modal.remove();
    });
    document.body.appendChild(modal);
  } catch (e) {
    toast(`Не удалось построить маршрут: ${e.message}`);
  } finally {
    if (btn) {
      btn.disabled = state.route.length < 2;
      btn.textContent = t('build_route');
    }
  }
}

export async function copyRoute(url) {
  try {
    await navigator.clipboard.writeText(url);
    toast('Ссылка скопирована');
  } catch {
    toast('Не удалось скопировать ссылку');
  }
}

export function openRoute(url) {
  if (!url) return;
  try {
    if (tg?.openLink) {
      tg.openLink(url, { try_instant_view: false });
      return;
    }
    window.open(url, '_blank', 'noopener,noreferrer');
  } catch {
    window.open(url, '_blank', 'noopener,noreferrer');
  }
}
