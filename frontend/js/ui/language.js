import { $ } from './helpers.js';

const DICT = {
  RU: {
    start_title:'Путешествуй по Беларуси', start_subtitle:'Достопримечательности, маршруты и погода', start:'Начать путешествие',
    region:'Выберите регион', region_search:'Поиск региона...', city_search:'Поиск города...', back:'Назад', weather:'Погода',
    weather_title:'Погода по городу', weather_empty:'Сначала выберите город в разделе «Путешествия»', choose_city:'Выбрать город',
    interests:'Интересы', interests_hint:'Можно выбрать несколько категорий', show_places:'Показать места', places:'Места',
    route:'Мой маршрут', build_route:'Построить маршрут', route_empty:'Маршрут пуст. Добавьте точки из карточек.',
    favorites:'Избранное', groups:'Группы', groups_hint:'Группы управляются через Telegram.',
    travel:'Путешествия', nothing:'Ничего не найдено', loading:'Загрузка…', searching:'JARVIS ищет места…',
    favorite:'Избранное', route_add:'Маршрут', route_ready:'Маршрут готов', distance:'Расстояние', open_maps:'Открыть Google Maps', copy:'Копировать ссылку',
    fav_empty:'Избранное пока пусто ❤️', tg_only:'Откройте приложение через Telegram.', weather_loading:'Загрузка погоды…', weather_failed:'Не удалось загрузить погоду',
    humidity:'Влажность', wind:'Ветер', pressure:'Давление', select_category:'Выберите хотя бы одну категорию', select_city:'Сначала выберите регион и город',
    regions_failed:'Не удалось загрузить регионы', cities_failed:'Не удалось загрузить города', places_failed:'Не удалось загрузить места',
    page:'Страница', place:'Место', address:'Адрес'
  },
  BY: {
    start_title:'Падарожнічай па Беларусі', start_subtitle:'Славутасці, маршруты і надвор’е', start:'Пачаць падарожжа',
    region:'Выберыце рэгіён', region_search:'Пошук рэгіёна...', city_search:'Пошук горада...', back:'Назад', weather:'Надвор’е',
    weather_title:'Надвор’е ў горадзе', weather_empty:'Спачатку выберыце горад у раздзеле «Падарожжы»', choose_city:'Выбраць горад',
    interests:'Інтарэсы', interests_hint:'Можна выбраць некалькі катэгорый', show_places:'Паказаць месцы', places:'Месцы',
    route:'Мой маршрут', build_route:'Пабудаваць маршрут', route_empty:'Маршрут пусты. Дадайце пункты з картак.',
    favorites:'Выбранае', groups:'Групы', groups_hint:'Групы кіруюцца праз Telegram.',
    travel:'Падарожжы', nothing:'Нічога не знойдзена', loading:'Загрузка…', searching:'JARVIS шукае месцы…',
    favorite:'Выбранае', route_add:'Маршрут', route_ready:'Маршрут гатовы', distance:'Адлегласць', open_maps:'Адкрыць Google Maps', copy:'Скапіяваць спасылку',
    fav_empty:'Выбранае пакуль пустое ❤️', tg_only:'Адкрыйце праграму праз Telegram.', weather_loading:'Загрузка надвор’я…', weather_failed:'Не ўдалося загрузіць надвор’е',
    humidity:'Вільготнасць', wind:'Вецер', pressure:'Ціск', select_category:'Выберыце хаця б адну катэгорыю', select_city:'Спачатку выберыце рэгіён і горад',
    regions_failed:'Не ўдалося загрузіць рэгіёны', cities_failed:'Не ўдалося загрузіць гарады', places_failed:'Не ўдалося загрузіць месцы',
    page:'Старонка', place:'Месца', address:'Адрас'
  }
};

export let currentLanguage = 'RU';
export const t = (key) => DICT[currentLanguage]?.[key] ?? DICT.RU[key] ?? key;

export function applyLanguage(lang, save=true) {
  currentLanguage = lang === 'BY' ? 'BY' : 'RU';
  const flag = $('#language-flag'), code = $('#language-code');
  if (flag) flag.textContent = currentLanguage === 'BY' ? '🇧🇾' : '🇷🇺';
  if (code) code.textContent = currentLanguage;
  document.documentElement.lang = currentLanguage === 'BY' ? 'be' : 'ru';

  document.querySelectorAll('[data-i18n]').forEach(el => {
    const key = el.dataset.i18n;
    if (key) el.textContent = t(key);
  });
  document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
    el.placeholder = t(el.dataset.i18nPlaceholder);
  });
  if (save) localStorage.setItem('jarvis-language', currentLanguage);
  window.dispatchEvent(new CustomEvent('jarvis:language', { detail: currentLanguage }));
}

export function toggleLanguage() {
  applyLanguage(currentLanguage === 'BY' ? 'RU' : 'BY');
}
