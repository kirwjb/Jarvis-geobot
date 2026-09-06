import { tg } from '../core/state.js';
import { $, haptic } from './helpers.js';

export function applyTheme(theme, save=true) {
  const light = theme === 'light';
  document.documentElement.classList.toggle('light-theme', light);
  document.body.classList.toggle('light-theme', light);
  const icon = $('#theme-icon');
  if (icon) icon.textContent = light ? '☾' : '☀';
  const button = $('#theme-toggle');
  if (button) button.setAttribute('aria-label', light ? 'Включить тёмную тему' : 'Включить светлую тему');
  try {
    const color = light ? '#f5f6f8' : '#0c0c0e';
    tg?.setHeaderColor?.(color); tg?.setBackgroundColor?.(color);
  } catch (_) {}
  if (save) localStorage.setItem('jarvis-theme', light ? 'light' : 'dark');
}

export function toggleTheme() {
  applyTheme(document.body.classList.contains('light-theme') ? 'dark' : 'light');
  haptic();
}
