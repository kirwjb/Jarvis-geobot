export const $ = (selector, root = document) => root.querySelector(selector);
export const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
export const esc = value => String(value ?? '').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#039;');

let toastTimer;
export function toast(message) {
  const el = $('#toast');
  if (!el) return;
  el.textContent = message;
  el.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.remove('show'), 2200);
}

const tgHaptic = () => window.Telegram?.WebApp?.HapticFeedback;

export function hapticImpact(style = 'light') {
  try {
    tgHaptic()?.impactOccurred?.(style);
  } catch (_) {}
}

export function hapticNotification(type = 'success') {
  try {
    tgHaptic()?.notificationOccurred?.(type);
  } catch (_) {}
}

export function hapticSelection() {
  try {
    tgHaptic()?.selectionChanged?.();
  } catch (_) {}
}

/** Unified haptic dispatcher with Telegram WebApp support and safe fallbacks. */
export function haptic(type = 'light') {
  if (type === 'selection') {
    hapticSelection();
  } else if (['success', 'warning', 'error'].includes(type)) {
    hapticNotification(type);
  } else {
    hapticImpact(type);
  }
}
