(() => {
  const DICT = {
    ru: {
      'Путешествуй по Беларуси': 'Путешествуй по Беларуси',
      'Достопримечательности, маршруты и погода': 'Достопримечательности, маршруты и погода',
      'Начать путешествие': 'Начать путешествие',
      'Выберите регион': 'Выберите регион',
      'Поиск региона...': 'Поиск региона...',
      'Регионы не найдены': 'Регионы не найдены',
      'Назад': 'Назад',
      'Область': 'Область',
      'Поиск города...': 'Поиск города...',
      'Города не найдены': 'Города не найдены',
      'Погода': 'Погода',
      'Погода по городу': 'Погода по городу',
      'Сначала выберите город в разделе «Путешествия»': 'Сначала выберите город в разделе «Путешествия»',
      'Выбрать город': 'Выбрать город',
      'Интересы': 'Интересы',
      'Можно выбрать несколько категорий': 'Можно выбрать несколько категорий',
      'Показать места': 'Показать места',
      'Места': 'Места',
      'Мой маршрут': 'Мой маршрут',
      'Построить маршрут': 'Построить маршрут',
      'Маршрут': 'Маршрут',
      'Путешествия': 'Путешествия',
      'Favorite': 'Избранное',
      'Route': 'Маршрут',
      'Влажность': 'Влажность',
      'Ветер': 'Ветер',
      'Давление': 'Давление',
      'Нет данных': 'Нет данных',
      'Загрузка погоды…': 'Загрузка погоды…',
      'Не удалось загрузить погоду': 'Не удалось загрузить погоду',
      'Загрузка городов…': 'Загрузка городов…',
      'Загрузка мест…': 'Загрузка мест…',
      'Ничего не найдено': 'Ничего не найдено',
      'Не удалось загрузить регионы': 'Не удалось загрузить регионы',
      'Не удалось загрузить города': 'Не удалось загрузить города',
      'Сначала выберите регион и город': 'Сначала выберите регион и город',
      'Выберите хотя бы одну категорию': 'Выберите хотя бы одну категорию',
      'Откройте приложение через Telegram для избранного': 'Откройте приложение через Telegram для избранного',
      'В избранном': 'В избранном',
      'Удалено из избранного': 'Удалено из избранного',
      'Добавлено в маршрут': 'Добавлено в маршрут',
      'Удалено из маршрута': 'Удалено из маршрута',
      'Архитектура': 'Архитектура', 'Природа': 'Природа', 'Музеи': 'Музеи', 'Храмы': 'Храмы',
      'Замки': 'Замки', 'Памятники': 'Памятники', 'Парки': 'Парки'
    },
    by: {
      'Путешествуй по Беларуси': 'Падарожнічай па Беларусі',
      'Достопримечательности, маршруты и погода': 'Славутасці, маршруты і надвор’е',
      'Начать путешествие': 'Пачаць падарожжа',
      'Выберите регион': 'Выберыце рэгіён',
      'Поиск региона...': 'Пошук рэгіёна...',
      'Регионы не найдены': 'Рэгіёны не знойдзены',
      'Назад': 'Назад',
      'Область': 'Вобласць',
      'Поиск города...': 'Пошук горада...',
      'Города не найдены': 'Гарады не знойдзены',
      'Погода': 'Надвор’е',
      'Погода по городу': 'Надвор’е па горадзе',
      'Сначала выберите город в разделе «Путешествия»': 'Спачатку выберыце горад у раздзеле «Падарожжы»',
      'Выбрать город': 'Выбраць горад',
      'Интересы': 'Інтарэсы',
      'Можно выбрать несколько категорий': 'Можна выбраць некалькі катэгорый',
      'Показать места': 'Паказаць месцы',
      'Места': 'Месцы',
      'Мой маршрут': 'Мой маршрут',
      'Построить маршрут': 'Пабудаваць маршрут',
      'Маршрут': 'Маршрут',
      'Путешествия': 'Падарожжы',
      'Favorite': 'Выбранае',
      'Route': 'Маршрут',
      'Влажность': 'Вільготнасць',
      'Ветер': 'Вецер',
      'Давление': 'Ціск',
      'Нет данных': 'Няма даных',
      'Загрузка погоды…': 'Загрузка надвор’я…',
      'Не удалось загрузить погоду': 'Не ўдалося загрузіць надвор’е',
      'Загрузка городов…': 'Загрузка гарадоў…',
      'Загрузка мест…': 'Загрузка месцаў…',
      'Ничего не найдено': 'Нічога не знойдзена',
      'Не удалось загрузить регионы': 'Не ўдалося загрузіць рэгіёны',
      'Не удалось загрузить города': 'Не ўдалося загрузіць гарады',
      'Сначала выберите регион и город': 'Спачатку выберыце рэгіён і горад',
      'Выберите хотя бы одну категорию': 'Выберыце хаця б адну катэгорыю',
      'Откройте приложение через Telegram для избранного': 'Адкрыйце праграму праз Telegram для выбранага',
      'В избранном': 'У выбраным',
      'Удалено из избранного': 'Выдалена з выбранага',
      'Добавлено в маршрут': 'Дададзена ў маршрут',
      'Удалено из маршрута': 'Выдалена з маршруту',
      'Архитектура': 'Архітэктура', 'Природа': 'Прырода', 'Музеи': 'Музеі', 'Храмы': 'Храмы',
      'Замки': 'Замкі', 'Памятники': 'Помнікі', 'Парки': 'Паркі'
    },
    en: {
      'Путешествуй по Беларуси': 'Travel around Belarus',
      'Достопримечательности, маршруты и погода': 'Sights, routes and weather',
      'Начать путешествие': 'Start exploring',
      'Выберите регион': 'Choose a region',
      'Поиск региона...': 'Search region...',
      'Регионы не найдены': 'No regions found',
      'Назад': 'Back',
      'Область': 'Region',
      'Поиск города...': 'Search city...',
      'Города не найдены': 'No cities found',
      'Погода': 'Weather',
      'Погода по городу': 'City weather',
      'Сначала выберите город в разделе «Путешествия»': 'First choose a city in the Travel section',
      'Выбрать город': 'Choose a city',
      'Интересы': 'Interests',
      'Можно выбрать несколько категорий': 'You can choose multiple categories',
      'Показать места': 'Show places',
      'Места': 'Places',
      'Мой маршрут': 'My route',
      'Построить маршрут': 'Build route',
      'Маршрут': 'Route',
      'Путешествия': 'Travel',
      'Favorite': 'Favorites',
      'Route': 'Route',
      'Влажность': 'Humidity',
      'Ветер': 'Wind',
      'Давление': 'Pressure',
      'Нет данных': 'No data',
      'Загрузка погоды…': 'Loading weather…',
      'Не удалось загрузить погоду': 'Could not load weather',
      'Загрузка городов…': 'Loading cities…',
      'Загрузка мест…': 'Loading places…',
      'Ничего не найдено': 'Nothing found',
      'Не удалось загрузить регионы': 'Could not load regions',
      'Не удалось загрузить города': 'Could not load cities',
      'Сначала выберите регион и город': 'Choose a region and city first',
      'Выберите хотя бы одну категорию': 'Choose at least one category',
      'Откройте приложение через Telegram для избранного': 'Open the app through Telegram to use favorites',
      'В избранном': 'Added to favorites',
      'Удалено из избранного': 'Removed from favorites',
      'Добавлено в маршрут': 'Added to route',
      'Удалено из маршрута': 'Removed from route',
      'Архитектура': 'Architecture', 'Природа': 'Nature', 'Музеи': 'Museums', 'Храмы': 'Churches',
      'Замки': 'Castles', 'Памятники': 'Monuments', 'Парки': 'Parks'
    }
  };

  const FLAGS = { ru: ['🇷🇺', 'RU'], by: ['🇧🇾', 'BY'], en: ['🇬🇧', 'EN'] };
  const LANGS = ['ru', 'by', 'en'];
  let current = localStorage.getItem('jarvis-language-v2') || localStorage.getItem('jarvis-language') || 'ru';
  current = current === 'RU' ? 'ru' : current === 'BY' ? 'by' : current === 'EN' ? 'en' : (LANGS.includes(current) ? current : 'ru');

  const reverse = {};
  Object.values(DICT).forEach(dict => Object.entries(dict).forEach(([source, value]) => {
    if (value) reverse[value] = source;
  }));

  function translateText(text) {
    const trimmed = String(text || '').trim();
    if (!trimmed) return text;
    const source = DICT.ru[trimmed] ? trimmed : (reverse[trimmed] || trimmed);
    const translated = DICT[current][source];
    if (!translated) return text;
    const start = String(text).indexOf(trimmed);
    const end = start + trimmed.length;
    return String(text).slice(0, start) + translated + String(text).slice(end);
  }

  function translateDom() {
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    const nodes = [];
    while (walker.nextNode()) nodes.push(walker.currentNode);
    nodes.forEach(node => {
      if (node.parentElement?.closest('script,style,svg')) return;
      const value = translateText(node.nodeValue);
      if (value !== node.nodeValue) node.nodeValue = value;
    });

    document.querySelectorAll('input[placeholder], textarea[placeholder]').forEach(input => {
      input.placeholder = translateText(input.placeholder);
    });

    const flag = document.getElementById('language-flag');
    const code = document.getElementById('language-code');
    if (flag && code) {
      flag.textContent = FLAGS[current][0];
      code.textContent = FLAGS[current][1];
    }
    document.documentElement.lang = current;
  }

  window.applyLanguage = function(language, save = true) {
    const normalized = String(language || '').toLowerCase();
    current = normalized === 'ru' || normalized === 'by' || normalized === 'en' ? normalized : 'ru';
    if (save) {
      localStorage.setItem('jarvis-language-v2', current);
      localStorage.setItem('jarvis-language', current.toUpperCase());
    }
    translateDom();
    if (window.haptic) window.haptic();
  };

  window.toggleLanguage = function() {
    const index = LANGS.indexOf(current);
    window.applyLanguage(LANGS[(index + 1) % LANGS.length]);
  };

  const observer = new MutationObserver(() => translateDom());
  observer.observe(document.body, { childList: true, subtree: true });

  setTimeout(() => window.applyLanguage(current, false), 0);
})();
