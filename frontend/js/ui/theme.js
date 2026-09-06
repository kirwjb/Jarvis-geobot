import { $, haptic } from './helpers.js';

export function applyTheme(theme, save=true) {
  const light = theme === 'light';
  document.documentElement.classList.toggle('light-theme', light);
  document.body.classList.toggle('light-theme', light);
  const icon = $('#theme-icon');
  if (icon) icon.textContent = light ? '☾' : '☀';
  const button = $('#theme-toggle');
  if (button) button.setAttribute('aria-label', light ? 'Включить тёмную тему' : 'Включить светлую тему');
  // Theme is local UI state. Do not call Telegram postMessage-backed color APIs here:
  // when the Mini App is proxied through Telegram Web, a mismatched ngrok origin can
  // produce noisy postMessage errors unrelated to application interaction.
  if (save) localStorage.setItem('jarvis-theme', light ? 'light' : 'dark');
}
export function toggleTheme(){applyTheme(document.body.classList.contains('light-theme')?'dark':'light');haptic();}
