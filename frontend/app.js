const tg = window.Telegram?.WebApp;
if (tg) {
  tg.ready();
  tg.expand();
}

const STORAGE_KEY = 'jarvis-geo-state';

function loadState() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return {};
    return JSON.parse(raw);
  } catch (error) {
    console.warn('Unable to load saved state:', error);
    return {};
  }
}

function saveState() {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({
      mode: S.mode,
      region: S.region,
      city: S.city,
      tags: [...S.tags],
      favs: [...S.favs],
      route: S.route,
      screen: getCurrentScreen()
    }));
  } catch (error) {
    console.warn('Unable to save state:', error);
  }
}

const savedState = loadState();

const S = {
  mode: savedState.mode || 'travel',
  region: savedState.region || null,
  city: savedState.city || null,
  tags: new Set(savedState.tags || []),
  favs: new Set(savedState.favs || []),
  route: Array.isArray(savedState.route) ? savedState.route : [],
  filtered: []
};

const API = '/api';

const REGIONS = [
  { id: 'minsk', name: 'Минская' },
  { id: 'brest', name: 'Брестская' },
  { id: 'grodno', name: 'Гродненская' },
  { id: 'gomel', name: 'Гомельская' },
  { id: 'mogilev', name: 'Могилёвская' },
  { id: 'vitebsk', name: 'Витебская' }
];

const CITIES = {
  minsk: [
    { name: 'Минск', w: { t: 22, d: 'Переменная облачность', h: 58, wind: 3.2, p: 1012 } },
    { name: 'Несвиж', w: { t: 21, d: 'Ясно', h: 55, wind: 2.8, p: 1013 } },
    { name: 'Мир', w: { t: 20, d: 'Облачно', h: 62, wind: 3.5, p: 1011 } },
    { name: 'Борисов', w: { t: 19, d: 'Пасмурно', h: 65, wind: 4.1, p: 1010 } }
  ],
  brest: [
    { name: 'Брест', w: { t: 24, d: 'Солнечно', h: 50, wind: 2.5, p: 1014 } },
    { name: 'Пинск', w: { t: 23, d: 'Ясно', h: 52, wind: 2.2, p: 1013 } },
    { name: 'Кобрин', w: { t: 22, d: 'Переменная облачность', h: 56, wind: 3.0, p: 1012 } }
  ],
  grodno: [
    { name: 'Гродно', w: { t: 21, d: 'Облачно', h: 60, wind: 3.3, p: 1011 } },
    { name: 'Лида', w: { t: 20, d: 'Пасмурно', h: 64, wind: 3.8, p: 1010 } },
    { name: 'Слоним', w: { t: 19, d: 'Дождь', h: 78, wind: 4.5, p: 1008 } }
  ],
  gomel: [
    { name: 'Гомель', w: { t: 23, d: 'Солнечно', h: 48, wind: 2.4, p: 1014 } },
    { name: 'Мозырь', w: { t: 22, d: 'Ясно', h: 50, wind: 2.6, p: 1013 } },
    { name: 'Речица', w: { t: 21, d: 'Переменная облачность', h: 55, wind: 3.1, p: 1012 } }
  ],
  mogilev: [
    { name: 'Могилёв', w: { t: 20, d: 'Пасмурно', h: 66, wind: 3.9, p: 1009 } },
    { name: 'Бобруйск', w: { t: 19, d: 'Облачно', h: 63, wind: 3.5, p: 1010 } },
    { name: 'Осиповичи', w: { t: 18, d: 'Дождь', h: 80, wind: 4.8, p: 1007 } }
  ],
  vitebsk: [
    { name: 'Витебск', w: { t: 19, d: 'Переменная облачность', h: 61, wind: 3.4, p: 1011 } },
    { name: 'Полоцк', w: { t: 18, d: 'Пасмурно', h: 67, wind: 4.0, p: 1009 } },
    { name: 'Новополоцк', w: { t: 18, d: 'Облачно', h: 65, wind: 3.7, p: 1010 } }
  ]
};

const TAGS = [
  { id: 'architecture', name: 'Архитектура' },
  { id: 'nature', name: 'Природа' },
  { id: 'museum', name: 'Музеи' },
  { id: 'church', name: 'Храмы' },
  { id: 'castle', name: 'Замки' },
  { id: 'monument', name: 'Памятники' },
  { id: 'park', name: 'Парки' }
];

const POIS = [
  { id: 1, name: 'Red Church', city: 'Минск', region: 'minsk', addr: 'Красный костёл', cat: 'church', rating: 4.8 },
  { id: 2, name: 'National Library', city: 'Минск', region: 'minsk', addr: 'Независимости 116', cat: 'architecture', rating: 4.7 },
  { id: 3, name: 'Mir Castle', city: 'Мир', region: 'minsk', addr: 'Мирский сельсовет', cat: 'castle', rating: 4.9 },
  { id: 4, name: 'Nesvizh Castle', city: 'Несвиж', region: 'minsk', addr: 'Замковая 2', cat: 'castle', rating: 4.8 },
  { id: 5, name: 'Brest Fortress', city: 'Брест', region: 'brest', addr: 'Территория крепости', cat: 'monument', rating: 4.9 },
  { id: 6, name: 'Belovezhskaya Pushcha', city: 'Брест', region: 'brest', addr: 'Каменюкский с/с', cat: 'nature', rating: 4.8 },
  { id: 7, name: 'Grodno Castle', city: 'Гродно', region: 'grodno', addr: 'Замковая 20', cat: 'castle', rating: 4.6 },
  { id: 8, name: 'Park Gorkogo', city: 'Минск', region: 'minsk', addr: 'Проспект Независимости', cat: 'park', rating: 4.5 },
  { id: 9, name: 'Museum of Great War', city: 'Минск', region: 'minsk', addr: 'Проспект Победителей 8', cat: 'museum', rating: 4.7 },
  { id: 10, name: 'Kolozhskaya Church', city: 'Гродно', region: 'grodno', addr: 'Коложский пер. 6', cat: 'church', rating: 4.6 },
  { id: 11, name: 'Rumyantsev Palace', city: 'Гомель', region: 'gomel', addr: 'Площадь Ленина 1', cat: 'architecture', rating: 4.5 },
  { id: 12, name: 'Bobruisk Fortress', city: 'Бобруйск', region: 'mogilev', addr: 'ул. Крепостная', cat: 'monument', rating: 4.4 }
];

function getCurrentScreen() {
  const active = document.querySelector('.screen.active');
  return active ? active.id : 'splash';
}

function go(id, options = {}) {
  const target = document.getElementById(id);
  if (!target) {
    console.error('Screen not found:', id);
    return;
  }
  document.querySelectorAll('.screen').forEach(screen => screen.classList.remove('active'));
  target.classList.add('active');
  const nav = document.getElementById('bottom-nav');
  if (nav) nav.style.display = id === 'splash' ? 'none' : 'flex';
  if (tg && tg.BackButton) {
    id === 'splash' ? tg.BackButton.hide() : tg.BackButton.show();
  }
  if (id === 'route') renderRoute();
  if (id === 'weather') renderWeatherScreen();
  if (!options.skipSave) saveState();
}

if (tg && tg.BackButton) {
  tg.BackButton.onClick(() => {
    const id = getCurrentScreen();
    if (id === 'regions') { go('splash'); return; }
    if (id === 'cities') { go('regions'); return; }
    if (id === 'weather') {
      S.mode === 'weather' ? go('cities') : go('tags');
      return;
    }
    if (id === 'tags') { go('cities'); return; }
    if (id === 'cards') { go('tags'); return; }
    if (id === 'route') goBackFromRoute();
  });
}

function toast(message) {
  const element = document.getElementById('toast');
  if (!element) return;
  element.textContent = message;
  element.classList.add('show');
  clearTimeout(element._toastTimer);
  element._toastTimer = setTimeout(() => element.classList.remove('show'), 2000);
}

function showToast(message) { toast(message); }

function haptic(type = 'light') {
  if (tg && tg.HapticFeedback && typeof tg.HapticFeedback.impactOccurred === 'function') {
    tg.HapticFeedback.impactOccurred(type);
  }
}

function updateFab() {
  const fab = document.getElementById('fab');
  const count = document.getElementById('fab-count');
  if (!fab || !count) return;
  count.textContent = S.route.length;
  S.route.length > 0 ? fab.classList.remove('hidden') : fab.classList.add('hidden');
}

function setActiveTab(tab) {
  document.querySelectorAll('.bottom-nav-item').forEach(item => {
    item.classList.toggle('active', item.dataset.tab === tab);
  });
}

function openTravel() {
  S.mode = 'travel';
  setActiveTab('travel');
  go('regions');
  haptic('light');
}

function openWeather() {
  S.mode = 'weather';
  setActiveTab('weather');
  if (S.city && S.region) {
    renderWeatherScreen();
    go('weather');
    haptic('light');
    return;
  }
  go('regions');
  haptic('light');
}

function bottomNavigate(tab) {
  if (tab === 'travel') { openTravel(); return; }
  if (tab === 'weather') { openWeather(); return; }
}

function renderRegions(list) {
  const grid = document.getElementById('regions-grid');
  if (!grid) return;
  grid.innerHTML = list.map(region => `
    <div class="card" onclick="pickRegion('${region.id}')">
      <span>${region.name}</span>
    </div>
  `).join('');
}

function filterRegions(query) {
  const q = query.toLowerCase().trim();
  renderRegions(REGIONS.filter(region => region.name.toLowerCase().includes(q)));
}

function pickRegion(id) {
  const region = REGIONS.find(item => item.id === id);
  if (!region) return;
  S.region = id;
  const regionCities = CITIES[id] || [];
  const cityStillValid = regionCities.some(city => city.name === S.city);
  if (!cityStillValid) S.city = null;
  document.getElementById('region-title').textContent = `${region.name} область`;
  renderCities(regionCities);
  go('cities');
}

function renderCities(list) {
  const grid = document.getElementById('cities-grid');
  if (!grid) return;
  grid.innerHTML = list.map((city, index) => `
    <div class="card ${S.city === city.name ? 'active' : ''}" onclick="pickCity('${city.name}', ${index})">
      <span>${city.name}</span>
    </div>
  `).join('');
}

function filterCities(query) {
  const q = query.toLowerCase().trim();
  const cities = CITIES[S.region] || [];
  renderCities(cities.filter(city => city.name.toLowerCase().includes(q)));
}

function pickCity(name, index) {
  const cities = CITIES[S.region] || [];
  const city = cities[index];
  if (!city) return;
  S.city = city.name;
  if (S.mode === 'weather') {
    renderWeatherScreen();
    go('weather');
    haptic('light');
    return;
  }
  S.mode = 'travel';
  renderTags();
  go('tags');
  haptic('light');
}

function renderWeatherScreen() {
  const empty = document.getElementById('weather-empty');
  const box = document.getElementById('weather-box');
  if (!empty || !box) return;
  if (!S.region || !S.city) {
    empty.style.display = 'flex';
    box.style.display = 'none';
    return;
  }
  const cities = CITIES[S.region] || [];
  const city = cities.find(item => item.name === S.city);
  if (!city) {
    empty.style.display = 'flex';
    box.style.display = 'none';
    return;
  }
  empty.style.display = 'none';
  box.style.display = 'block';
  renderWeather(city);
}

function renderWeather(city) {
  const box = document.getElementById('weather-box');
  if (!box || !city || !city.w) return;
  const w = city.w;
  box.innerHTML = `
    <div class="weather-card">
      <div class="weather-city">${city.name}</div>
      <div class="weather-main">
        <div class="weather-temp">${w.t}°</div>
        <div class="weather-desc">${w.d}</div>
      </div>
      <div class="weather-details">
        <div><span>Влажность</span><strong>${w.h}%</strong></div>
        <div><span>Ветер</span><strong>${w.wind} м/с</strong></div>
        <div><span>Давление</span><strong>${w.p} hPa</strong></div>
      </div>
    </div>
  `;
}

function prepareWeatherButton() {
  const button = document.querySelector('#weather .weather-go-btn');
  if (!button) return;
  button.onclick = () => {
    S.mode = 'weather';
    setActiveTab('weather');
    go('regions');
  };
}

function renderTags() {
  const list = document.getElementById('tags-list');
  const button = document.getElementById('btn-tags');
  if (!list) return;
  list.innerHTML = TAGS.map(tag => `
    <button type="button" class="tag ${S.tags.has(tag.id) ? 'active' : ''}" onclick="toggleTag('${tag.id}')">
      ${tag.name}
    </button>
  `).join('');
  if (button) button.disabled = S.tags.size === 0;
}

function toggleTag(id) {
  S.tags.has(id) ? S.tags.delete(id) : S.tags.add(id);
  renderTags();
  saveState();
  haptic('light');
}

function loadCards() {
  S.filtered = POIS.filter(place => {
    const sameRegion = place.region === S.region;
    const sameCity = !S.city || place.city === S.city;
    const sameCategory = S.tags.has(place.cat);
    return sameRegion && sameCity && sameCategory;
  });
  const title = document.getElementById('cards-title');
  if (title) title.textContent = S.city || 'Места';
  renderFeed();
  go('cards');
}

function renderFeed() {
  const feed = document.getElementById('feed');
  if (!feed) return;
  if (S.filtered.length === 0) {
    feed.innerHTML = `<div style="text-align:center;padding:50px;color:var(--muted);">Ничего не найдено</div>`;
    return;
  }
  feed.innerHTML = S.filtered.map(place => {
    const isFavorite = S.favs.has(place.id);
    const inRoute = S.route.some(item => item.id === place.id);
    return `
      <div class="poi-card">
        <div class="poi-img">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1">
            <path d="M3 21h18 M5 21V7l8-4 8 4v14 M9 21v-6h6v6"/>
          </svg>
        </div>
        <div class="poi-body">
          <div class="poi-name">${place.name}</div>
          <div class="poi-rating"><span class="star">★</span><span class="val">${place.rating}</span></div>
          <div class="poi-loc">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 2 C8 2 5 5 5 9 c0 5 7 13 7 13 s7-8 7-13 c0-4-3-7-7-7z"/>
              <circle cx="12" cy="9" r="2.5"/>
            </svg>
            ${place.city}
          </div>
          <div class="poi-actions">
            <button class="poi-act ${isFavorite ? 'active' : ''}" type="button" onclick="toggleFav(${place.id})">
              <svg viewBox="0 0 24 24" fill="${isFavorite ? 'currentColor' : 'none'}" stroke="currentColor" stroke-width="2">
                <path d="M20.84 4.61 a5.5 5.5 0 0 0-7.78 0 L12 5.67 l-1.06-1.06 a5.5 5.5 0 0 0-7.78 7.78 l1.06 1.06 L12 21.23 l7.78-7.78 1.06-1.06 a5.5 5.5 0 0 0 0-7.78z"/>
              </svg>
              Favorite
            </button>
            <button class="poi-act ${inRoute ? 'active' : ''}" type="button" onclick="toggleRoute(${place.id})">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M12 2L2 7l10 5 10-5-10-5z M2 17l10 5 10-5 M2 12l10 5 10-5"/>
              </svg>
              Route
            </button>
          </div>
        </div>
      </div>
    `;
  }).join('');
}

function toggleFav(id) {
  S.favs.has(id) ? S.favs.delete(id) : S.favs.add(id);
  toast(S.favs.has(id) ? 'В избранном' : 'Удалено из избранного');
  renderFeed();
  saveState();
  haptic('light');
}

function toggleRoute(id) {
  const existing = S.route.find(item => item.id === id);
  if (existing) {
    S.route = S.route.filter(item => item.id !== id);
    toast('Удалено из маршрута');
  } else {
    const place = POIS.find(item => item.id === id);
    if (place) {
      S.route.push(place);
      toast('Добавлено в маршрут');
    }
  }
  updateFab();
  renderFeed();
  saveState();
}

function goBackFromRoute() {
  S.filtered.length > 0 ? go('cards') : go('tags');
}

function renderRoute() {
  const list = document.getElementById('route-list');
  const button = document.getElementById('btn-build');
  if (!list || !button) return;
  if (S.route.length === 0) {
    list.innerHTML = `<div class="route-empty">Маршрут пуст.<br>Добавьте точки из карточек.</div>`;
    button.disabled = true;
    return;
  }
  button.disabled = S.route.length < 2;
  list.innerHTML = S.route.map((place, index) => `
    <div class="route-item">
      <div class="route-num">${index + 1}</div>
      <div class="route-info">
        <div class="route-name">${place.name}</div>
        <div class="route-city">${place.city}</div>
      </div>
      <button class="route-del" type="button" onclick="removeRoute(${place.id})">✕</button>
    </div>
  `).join('');
}

function removeRoute(id) {
  S.route = S.route.filter(item => item.id !== id);
  updateFab();
  renderRoute();
  saveState();
}

function buildRoute() {
  toast('Маршрут построен!');
  if (tg && tg.HapticFeedback) tg.HapticFeedback.notificationOccurred('success');
}

function applyTheme(theme, save = true) {
  const normalized = theme === 'light' ? 'light' : 'dark';
  const isLight = normalized === 'light';
  document.documentElement.classList.toggle('light-theme', isLight);
  document.body.classList.toggle('light-theme', isLight);
  const icon = document.getElementById('theme-icon');
  if (icon) icon.textContent = isLight ? '☾' : '☀';
  const button = document.getElementById('theme-toggle');
  if (button) {
    button.setAttribute('aria-label', isLight ? 'Включить тёмную тему' : 'Включить светлую тему');
    button.setAttribute('title', isLight ? 'Включить тёмную тему' : 'Включить светлую тему');
  }
  const meta = document.getElementById('theme-color-meta');
  if (meta) meta.setAttribute('content', isLight ? '#f5f6f8' : '#0c0c0e');
  if (tg) {
    const color = isLight ? '#f5f6f8' : '#0c0c0e';
    try {
      if (typeof tg.setHeaderColor === 'function') tg.setHeaderColor(color);
      if (typeof tg.setBackgroundColor === 'function') tg.setBackgroundColor(color);
    } catch (error) {
      console.warn('Telegram theme update failed:', error);
    }
  }
  if (save) localStorage.setItem('jarvis-theme', normalized);
}

function toggleTheme() {
  const isLight = document.body.classList.contains('light-theme');
  applyTheme(isLight ? 'dark' : 'light', true);
  haptic('light');
}

function applyLanguage(language, save = true) {
  const lang = language === 'RU' ? 'RU' : 'BY';
  const flag = document.getElementById('language-flag');
  const code = document.getElementById('language-code');
  if (flag) flag.textContent = lang === 'BY' ? '🇧🇾' : '🇷🇺';
  if (code) code.textContent = lang;
  const button = document.getElementById('language-toggle');
  if (button) {
    button.setAttribute('aria-label', `Язык: ${lang}`);
    button.setAttribute('title', `Язык: ${lang}`);
  }
  document.documentElement.lang = lang === 'BY' ? 'be' : 'ru';
  if (save) localStorage.setItem('jarvis-language', lang);
}

function toggleLanguage() {
  const current = localStorage.getItem('jarvis-language') || 'BY';
  const next = current === 'BY' ? 'RU' : 'BY';
  applyLanguage(next, true);
  toast(next === 'BY' ? 'Выбран язык BY' : 'Выбран язык RU');
  haptic('light');
}

function init() {
  renderRegions(REGIONS);
  renderTags();
  updateFab();
  const savedTheme = localStorage.getItem('jarvis-theme') || 'dark';
  applyTheme(savedTheme, false);
  const savedLanguage = localStorage.getItem('jarvis-language') || 'BY';
  applyLanguage(savedLanguage, false);
  prepareWeatherButton();
  if (S.region) {
    const region = REGIONS.find(item => item.id === S.region);
    if (region) {
      const title = document.getElementById('region-title');
      if (title) title.textContent = `${region.name} область`;
      renderCities(CITIES[S.region] || []);
    }
  }
  const savedScreen = savedState.screen || null;
  let screen = savedScreen;
  if (screen === 'weather' && (!S.region || !S.city)) {
    S.mode = 'weather';
    screen = 'regions';
  }
  if (['tags', 'cards'].includes(screen) && (!S.region || !S.city)) {
    S.mode = 'travel';
    screen = 'regions';
  }
  const hasSavedSession = Boolean(savedScreen || S.region || S.city);
  if (hasSavedSession && screen && document.getElementById(screen)) {
    S.mode === 'weather' ? setActiveTab('weather') : setActiveTab('travel');
    go(screen, { skipSave: true });
    if (screen === 'weather') renderWeatherScreen();
    if (screen === 'cards' && S.region && S.city) loadCards();
  } else {
    setActiveTab('travel');
    go('splash', { skipSave: true });
  }
  const nav = document.getElementById('bottom-nav');
  if (nav && getCurrentScreen() === 'splash') nav.style.display = 'none';
}

init();