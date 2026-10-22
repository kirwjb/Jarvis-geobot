import { state, persist, tg } from './state.js?v=20261017-010';
import { $, $$ } from '../ui/helpers.js?v=20261017-010';

let backButtonBound = false;

export function go(id, {save=true}={}) {
  const target = document.getElementById(id);
  if (!target) return false;
  $$('.screen').forEach(screen => screen.classList.remove('active'));
  target.classList.add('active');
  if (state.screen && state.screen !== id) {
    state.previousScreen = state.screen;
  }
  state.screen = id;
  const nav = $('#bottom-nav');
  if (nav) nav.style.display = id === 'splash' ? 'none' : 'flex';
  if (id === 'weather') {
    setTab('weather');
  } else if (id === 'favorites') {
    setTab('favorites');
  } else if (id === 'route') {
    setTab('route');
  } else if (['regions', 'cities', 'tags', 'cards'].includes(id)) {
    setTab('travel');
  }
  try { id === 'splash' ? tg?.BackButton?.hide?.() : tg?.BackButton?.show?.(); } catch (_) {}
  try { tg?.MainButton?.hide?.(); } catch (_) {}
  if (save) persist();
  return true;
}

export function initTelegramBackButton() {
  if (backButtonBound || !tg?.BackButton?.onClick) return;
  backButtonBound = true;
  tg.BackButton.onClick(() => {
    const map = { regions:'splash', cities:'regions', tags:'cities', cards:'tags' };
    if (state.screen === 'favorites') {
      return go(state.previousScreen && state.previousScreen !== 'favorites' ? state.previousScreen : 'splash');
    }
    if (state.screen === 'weather') {
      const fallback = (state.region && state.city && state.tags?.size > 0 && state.pois?.length > 0) ? 'cards'
        : (state.region && state.city) ? 'tags'
        : state.region ? 'cities' : 'splash';
      const prev = state.previousScreen && state.previousScreen !== 'weather' ? state.previousScreen : fallback;
      if (prev === 'cards' && (!state.tags?.size || !state.pois?.length)) {
        return go(state.region && state.city ? 'tags' : 'regions');
      }
      return go(prev);
    }
    if (state.screen === 'route') return go(state.previousScreen && state.previousScreen !== 'route' ? state.previousScreen : (state.pois.length ? 'cards' : 'splash'));
    if (map[state.screen]) go(map[state.screen]);
  });
}

export function setTab(tab) {
  $$('.bottom-nav-item').forEach(item => item.classList.toggle('active', item.dataset.tab === tab));
}

export function bindNavigation() {}
