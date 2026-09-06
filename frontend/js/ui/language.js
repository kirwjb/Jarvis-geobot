import { $ } from './helpers.js';

export function applyLanguage(lang, save=true) {
  const value = lang === 'BY' ? 'BY' : 'RU';
  const flag = $('#language-flag'), code = $('#language-code');
  if (flag) flag.textContent = value === 'BY' ? '🇧🇾' : '🇷🇺';
  if (code) code.textContent = value;
  document.documentElement.lang = value === 'BY' ? 'be' : 'ru';
  if (save) localStorage.setItem('jarvis-language', value);
}

export function toggleLanguage() {
  const current = localStorage.getItem('jarvis-language') || 'RU';
  applyLanguage(current === 'BY' ? 'RU' : 'BY');
}
