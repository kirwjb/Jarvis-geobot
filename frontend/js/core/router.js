import { state, persist, tg } from './state.js';
import { $, $$, haptic } from '../ui/helpers.js';

export function go(id, {save=true}={}) {
  const target = document.getElementById(id);
  if (!target) return false;
  $$('.screen').forEach(s => s.classList.remove('active'));
  target.classList.add('active');
  state.screen = id;
  const nav = $('#bottom-nav');
  if (nav) nav.style.display = id === 'splash' ? 'none' : 'flex';
  try { id === 'splash' ? tg?.BackButton?.hide?.() : tg?.BackButton?.show?.(); } catch (_) {}
  if (save) persist();
  return true;
}

export function initTelegramBackButton() {
  tg?.BackButton?.onClick?.(() => {
    const map = {regions:'splash', cities:'regions', tags:'cities', cards:'tags'};
    if (state.screen === 'weather') return go(state.mode === 'weather' ? 'cities' : 'tags');
    if (state.screen === 'route') return go(state.pois.length ? 'cards' : 'tags');
    if (state.screen === 'favorites') return go('cards');
    if (state.screen === 'groups') return go('cards');
    if (map[state.screen]) go(map[state.screen]);
  });
}

export function setTab(tab) {
  $$('.bottom-nav-item').forEach(item => item.classList.toggle('active', item.dataset.tab === tab));
}

export function bindNavigation() {
  $('#bottom-nav')?.addEventListener('click', e => {
    const item = e.target.closest('.bottom-nav-item');
    if (!item) return;

    // The POI feed is a focused screen. Once it is open, bottom-tab
    // navigation must not destroy it. Leaving the feed is only possible
    // through the Back button (Telegram BackButton or the screen's Back UI).
    if (state.screen === 'cards') {
      e.preventDefault();
      e.stopImmediatePropagation();
      haptic();
      return;
    }

    const tab = item.dataset.tab;
    if (tab === 'travel') { state.mode='travel'; setTab(tab); go('regions'); }
    if (tab === 'weather') { state.mode='weather'; setTab(tab); go(state.city && state.region ? 'weather' : 'regions'); }
    haptic();
  });
}
