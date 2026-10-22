import { $, haptic } from './helpers.js?v=20261017-010';
import { ICONS } from './icons.js?v=20261017-010';

const tg = window.Telegram?.WebApp;

export function syncTelegramStylingVariables(light) {
  const root = document.documentElement;

  if (light) {
    root.style.setProperty('--tg-theme-bg-color', '#ffffff');
    root.style.setProperty('--tg-theme-text-color', '#0f172a');
    root.style.setProperty('--tg-theme-hint-color', '#64748b');
    root.style.setProperty('--tg-theme-link-color', '#007aff');
    root.style.setProperty('--tg-theme-button-color', '#007aff');
    root.style.setProperty('--tg-theme-button-text-color', '#ffffff');
    root.style.setProperty('--tg-theme-secondary-bg-color', '#f8fafc');
    root.style.setProperty('--tg-theme-header-bg-color', '#ffffff');
    root.style.setProperty('--tg-theme-bottom-bar-bg-color', '#ffffff');
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

export function applyTheme(theme, save = true) {
  const light = theme === 'light';
  document.documentElement.classList.toggle('light-theme', light);
  document.body.classList.toggle('light-theme', light);
  document.documentElement.classList.toggle('dark-theme', !light);
  document.body.classList.toggle('dark-theme', !light);
  document.documentElement.setAttribute('data-theme', light ? 'light' : 'dark');

  syncTelegramStylingVariables(light);

  const icon = $('#theme-icon');
  if (icon) icon.innerHTML = light ? ICONS.moon : ICONS.sun;

  const button = $('#theme-toggle');
  if (button) {
    const label = light ? 'Включить тёмную тему' : 'Включить светлую тему';
    button.setAttribute('aria-label', label);
    button.setAttribute('title', label);
  }

  try {
    const bgColor = light ? '#ffffff' : '#0f141c';
    if (tg?.setHeaderColor) tg.setHeaderColor(bgColor);
    if (tg?.setBackgroundColor) tg.setBackgroundColor(bgColor);
  } catch (_) {}

  try {
    const metaThemeColor = document.querySelector('meta[name="theme-color"]');
    if (metaThemeColor) {
      metaThemeColor.setAttribute('content', light ? '#f7f8fa' : '#0c0c0e');
    }
  } catch (_) {}

  if (save) localStorage.setItem('jarvis-theme', light ? 'light' : 'dark');
}

export function toggleTheme() {
  const saved = localStorage.getItem('jarvis-theme');
  const isLight = saved !== null
    ? saved === 'light'
    : (document.documentElement.classList.contains('light-theme') || document.body.classList.contains('light-theme'));
  applyTheme(isLight ? 'dark' : 'light', true);
  haptic('light');
}

if (typeof window !== 'undefined') {
  window.toggleTheme = toggleTheme;
}

export function syncTelegramTheme() {
  const saved = localStorage.getItem('jarvis-theme');
  if (!saved && tg?.colorScheme) {
    applyTheme(tg.colorScheme, false);
  }
}

try {
  tg?.onEvent?.('themeChanged', () => {
    if (!localStorage.getItem('jarvis-theme')) {
      syncTelegramTheme();
    }
  });
} catch (_) {}
