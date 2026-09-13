import { state, persist, tg } from './state.js';
import { $, $$ } from '../ui/helpers.js';

/** Activate one screen and keep Telegram BackButton plus persisted screen state in sync. */
export function go(id, {save=true}={}) {
  const target = document.getElementById(id);
  if (!target) return false;
  $$('.screen').forEach(screen => screen.classList.remove('active'));
  target.classList.add('active');
  state.screen = id;
  const nav = $('#bottom-nav');
  if (nav) nav.style.display = id === 'splash' ? 'none' : 'flex';
  try { id === 'splash' ? tg?.BackButton?.hide?.() : tg?.BackButton?.show?.(); } catch (_) {}
  if (save) persist();
  return true;
}

/** Configure Telegram's native Back button as the only way out of a focused POI feed. */
export function initTelegramBackButton() {
  tg?.BackButton?.onClick?.(() => {
    const map = { regions:'splash', cities:'regions', tags:'cities', cards:'tags', favorites:'splash', groups:'splash', group:'groups' };
    if (state.screen === 'weather') return go(state.mode === 'weather' ? 'cities' : 'tags');
    if (state.screen === 'route') return go(state.pois.length ? 'cards' : 'tags');
    if (map[state.screen]) go(map[state.screen]);
  });
}

/** Mark the selected bottom-navigation item; actual navigation is owned by app/events.js. */
export function setTab(tab) {
  $$('.bottom-nav-item').forEach(item => item.classList.toggle('active', item.dataset.tab === tab));
}

/** Kept as a compatibility no-op; event delegation is now installed in one place only. */
export function bindNavigation() {}
