import { $ } from './helpers.js?v=20261017-010';
import { ICONS } from './icons.js?v=20261017-010';

const DICT = {
  RU: {
    start_title:'Путешествуй по Беларуси', start_subtitle:'Достопримечательности, маршруты и погода', start:'Начать путешествие',
    region:'Выберите регион', region_search:'Поиск региона...', city_search:'Поиск города...', back:'Назад', weather:'Погода',
    weather_title:'Погода по городу', weather_empty:'Выберите город выше или воспользуйтесь поиском', choose_city:'Выбрать город',
    weather_popular:'Популярные города',
    interests:'Интересы', interests_hint:'Можно выбрать несколько категорий', show_places:'Показать места', places:'Места',
    route:'Маршрут', my_route:'Мой маршрут', route_title:'Мой маршрут', build_route:'Построить маршрут', route_empty:'Маршрут пуст. Добавьте точки из карточек.',
    favorites:'Избранное', travel:'Путешествия',
    architecture:'Архитектура', nature:'Природа', museum:'Музеи', church:'Храмы', castle:'Замки', monument:'Памятники', park:'Парки',
    nothing:'Ничего не найдено', loading:'Загрузка…', searching:'JARVIS ищет места…', favorite:'Избранное', route_add:'Маршрут',
    route_ready:'Маршрут готов', distance:'Расстояние', open_maps:'Открыть Google Maps', copy:'Копировать ссылку', fav_empty:'Избранное пока пусто',
    tg_only:'Откройте приложение через Telegram.', weather_loading:'Загрузка погоды…', weather_failed:'Не удалось загрузить погоду',
    humidity:'Влажность', wind:'Ветер', pressure:'Давление', select_category:'Выберите хотя бы одну категорию', select_city:'Сначала выберите регион и город',
    regions_failed:'Не удалось загрузить регионы', cities_failed:'Не удалось загрузить города', places_failed:'Не удалось загрузить места', page:'Страница', place:'Место', address:'Адрес',
    poi_search:'Поиск мест...', shuffle:'Перемешать',
    weather_cached:'JARVIS использует свежий кэш', weather_updated:'JARVIS обновил данные сейчас',
    feels_like:'Ощущается как', sunrise:'Восход', sunset:'Закат', hourly:'По часам', forecast_3days:'Прогноз на 3 дня',
    legal:'Правовая информация',
    nav_travel:'Путешествия', nav_route:'Маршрут', nav_weather:'Погода', nav_favorites:'Избранное',
    research_expand:'Исследовать окрестности (+25 км)', research_searching:'Ищем неизведанные места вокруг...',
    research_found:'Найдено новых мест: ', research_none:'Все места в окрестностях уже добавлены!',
    research_all_seen:'Вы просмотрели все доступные места.',
    report_photo:'Пожаловаться', delete_photo:'Удалить',
    report_prompt:'Укажите причину жалобы (неприемлемое фото, конфликт, политика, насилие, ошибка):',
    report_default_reason:'Неприемлемое изображение',
    report_sent:'Жалоба принята на рассмотрение. Спасибо!',
    delete_photo_confirm:'Вы действительно хотите удалить и заблокировать это фото?',
    photo_deleted:'Фотография успешно удалена и заблокирована.',
    report_error:'Ошибка отправки жалобы:',
    delete_error:'Ошибка удаления фото:',
    close:'Закрыть'
  },
  BY: {
    start_title:'Падарожнічай па Беларусі', start_subtitle:'Славутасці, маршруты і надвор’е', start:'Пачаць падарожжа',
    region:'Выберыце рэгіён', region_search:'Пошук рэгіёна...', city_search:'Пошук горада...', back:'Назад', weather:'Надвор’е',
    weather_title:'Надвор’е ў горадзе', weather_empty:'Выберыце горад вышэй або скарыстайцеся пошукам', choose_city:'Выбраць горад',
    weather_popular:'Папулярныя гарады',
    interests:'Інтарэсы', interests_hint:'Можна выбраць некалькі катэгорый', show_places:'Паказаць месцы', places:'Месцы',
    route:'Маршрут', my_route:'Мой маршрут', route_title:'Мой маршрут', build_route:'Пабудаваць маршрут', route_empty:'Маршрут пусты. Дадайце пункты з картак.',
    favorites:'Выбранае', travel:'Падарожжы',
    architecture:'Архітэктура', nature:'Прырода', museum:'Музеі', church:'Храмы', castle:'Замкі', monument:'Помнікі', park:'Паркі',
    nothing:'Нічога не знойдзена', loading:'Загрузка…', searching:'JARVIS шукае месцы…', favorite:'Выбранае', route_add:'Маршрут',
    route_ready:'Маршрут гатовы', distance:'Адлегласць', open_maps:'Адкрыць Google Maps', copy:'Скапіяваць спасылку', fav_empty:'Выбранае пакуль пустое',
    tg_only:'Адкрыйце праграму праз Telegram.', weather_loading:'Загрузка надвор’я…', weather_failed:'Не ўдалося загрузіць надвор’е',
    humidity:'Вільготнасць', wind:'Вецер', pressure:'Ціск', select_category:'Выберыце хаця б адну катэгорыю', select_city:'Спачатку выберыце рэгіён і горад',
    regions_failed:'Не ўдалося загрузіць рэгіёны', cities_failed:'Не ўдалося загрузіць гарады', places_failed:'Не ўдалося загрузіць месцы', page:'Старонка', place:'Месца', address:'Адрас',
    poi_search:'Пошук месцаў...', shuffle:'Перамяшаць',
    weather_cached:'JARVIS выкарыстоўвае свежы кэш', weather_updated:'JARVIS абнавіў дадзеныя зараз',
    feels_like:'Адчуваецца як', sunrise:'Узыход', sunset:'Заход', hourly:'Па гадзінах', forecast_3days:'Прагноз на 3 дні',
    legal:'Прававая інфармацыя',
    nav_travel:'Падарожжы', nav_route:'Маршрут', nav_weather:"Надвор'е", nav_favorites:'Выбранае',
    research_expand:'Даследаваць ваколіцы (+25 км)', research_searching:'Шукаем нязведаныя месцы навокал...',
    research_found:'Знойдзена новых месцаў: ', research_none:'Усе месцы ў ваколіцах ужо дададзеныя!',
    research_all_seen:'Вы прагледзелі ўсе даступныя месцы.',
    report_photo:'Паскардзіцца', delete_photo:'Выдаліць',
    report_prompt:'Пазначце прычыну скаргі (непрымальнае фота, канфлікт, палітыка, гвалт, памылка):',
    report_default_reason:'Непрымальная выява',
    report_sent:'Скарга прынята на разгляд. Дзякуй!',
    delete_photo_confirm:'Вы сапраўды хочаце выдаліць і заблакаваць гэтае фота?',
    photo_deleted:'Фота паспяхова выдалена і заблакавана.',
    report_error:'Памылка адпраўкі скаргі:',
    delete_error:'Памылка выдалення фота:',
    close:'Закрыць'
  }
};

export let currentLanguage = 'RU';
export const t = (key) => DICT[currentLanguage]?.[key] ?? DICT.RU[key] ?? key;

export function applyLanguage(lang, save=true) {
  currentLanguage = lang === 'BY' ? 'BY' : 'RU';
  const flag = $('#language-flag'), code = $('#language-code');
  if (flag) flag.innerHTML = ICONS.globe;
  if (code) code.textContent = currentLanguage;
  document.documentElement.lang = currentLanguage === 'BY' ? 'be' : 'ru';
  document.querySelectorAll('[data-i18n]').forEach(el => { const key=el.dataset.i18n; if(key)el.textContent=t(key); });
  document.querySelectorAll('[data-i18n-placeholder]').forEach(el => { el.placeholder=t(el.dataset.i18nPlaceholder); });
  if (save) localStorage.setItem('jarvis-language', currentLanguage);
  window.dispatchEvent(new CustomEvent('jarvis:language', { detail: currentLanguage }));
}
export function toggleLanguage(){applyLanguage(currentLanguage === 'BY' ? 'RU' : 'BY');}
