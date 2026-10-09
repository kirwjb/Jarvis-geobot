import { $, haptic } from './helpers.js?v=20261009002';

const tg = window.Telegram?.WebApp;

/** Sync Telegram's native styling variables to the active theme. */
export function syncTelegramStylingVariables(light) {
  const root = document.documentElement;
  // We rely on style.css for custom variables now. 
  // Only override tg-theme vars if needed for fallback
  if (light) {
    root.style.setProperty('--tg-theme-bg-color', '#f6f8fc');
    root.style.setProperty('--tg-theme-text-color', '#12141a');
    root.style.setProperty('--tg-theme-hint-color', '#6b7280');
    root.style.setProperty('--tg-theme-link-color', '#2563eb');
    root.style.setProperty('--tg-theme-button-color', '#2563eb');
    root.style.setProperty('--tg-theme-button-text-color', '#ffffff');
    root.style.setProperty('--tg-theme-secondary-bg-color', 'rgba(255,255,255,0.65)');
    root.style.setProperty('--tg-theme-header-bg-color', '#f6f8fc');
    root.style.setProperty('--tg-theme-bottom-bar-bg-color', '#f6f8fc');
  } else {
    root.style.setProperty('--tg-theme-bg-color', '#0b0f17');
    root.style.setProperty('--tg-theme-text-color', '#f4f6fa');
    root.style.setProperty('--tg-theme-hint-color', '#9ca3af');
    root.style.setProperty('--tg-theme-link-color', '#3b82f6');
    root.style.setProperty('--tg-theme-button-color', '#3b82f6');
    root.style.setProperty('--tg-theme-button-text-color', '#ffffff');
    root.style.setProperty('--tg-theme-secondary-bg-color', 'rgba(22, 27, 34, 0.7)');
    root.style.setProperty('--tg-theme-header-bg-color', '#0b0f17');
    root.style.setProperty('--tg-theme-bottom-bar-bg-color', '#0b0f17');
  }
}

/** Set the active application theme with CSS class toggles, Telegram variables, and accessibility labels. */
export function applyTheme(theme, save = true) {
  const light = theme === 'light';
  document.documentElement.classList.toggle('light-theme', light);
  document.body.classList.toggle('light-theme', light);
  document.documentElement.classList.toggle('dark-theme', !light);
  document.body.classList.toggle('dark-theme', !light);
  document.documentElement.setAttribute('data-theme', light ? 'light' : 'dark');

  // Sync Telegram's standard CSS variables on :root
  syncTelegramStylingVariables(light);

  const icon = $('#theme-icon');
  if (icon) icon.textContent = light ? '☾' : '☀';

  const button = $('#theme-toggle');
  if (button) {
    const label = light ? 'Включить тёмную тему' : 'Включить светлую тему';
    button.setAttribute('aria-label', label);
    button.setAttribute('title', label);
  }

  // Sync Telegram WebApp native top/bottom colors if running in Telegram
  try {
    const bgColor = light ? '#f7f8fa' : '#0d0f14';
    if (tg?.setHeaderColor) tg.setHeaderColor(bgColor);
    if (tg?.setBackgroundColor) tg.setBackgroundColor(bgColor);
  } catch (_) {}

  // Update browser theme-color meta tag
  try {
    const metaThemeColor = document.querySelector('meta[name="theme-color"]');
    if (metaThemeColor) {
      metaThemeColor.setAttribute('content', light ? '#f7f8fa' : '#0c0c0e');
    }
  } catch (_) {}

  if (save) localStorage.setItem('jarvis-theme', light ? 'light' : 'dark');
}

/** Toggle between light and dark themes with haptic feedback. */
export function toggleTheme() {
  const saved = localStorage.getItem('jarvis-theme');
  const isLight = saved !== null
    ? saved === 'light'
    : (document.documentElement.classList.contains('light-theme') || document.body.classList.contains('light-theme'));
  applyTheme(isLight ? 'dark' : 'light', true);
  haptic('light');
}

// Expose globally for backup inline event handlers
if (typeof window !== 'undefined') {
  window.toggleTheme = toggleTheme;
}

/** Sync theme from Telegram colorScheme if user hasn't set an explicit preference. */
export function syncTelegramTheme() {
  const saved = localStorage.getItem('jarvis-theme');
  if (!saved && tg?.colorScheme) {
    applyTheme(tg.colorScheme, false);
  }
}

// Subscribe to Telegram theme changes if user hasn't overridden
try {
  tg?.onEvent?.('themeChanged', () => {
    if (!localStorage.getItem('jarvis-theme')) {
      syncTelegramTheme();
    }
  });
} catch (_) {}
