const tg = window.Telegram?.WebApp;
if (tg) {
  tg.ready();
  tg.expand();
}

const API = '/api';
const STORAGE_KEY = 'jarvis-geo-state';

const TAGS = [
  { id: 'architecture', name: 'Архитектура' },
  { id: 'nature', name: 'Природа' },
  { id: 'museum', name: 'Музеи' },
  { id: 'church', name: 'Храмы' },
  { id: 'castle', name: 'Замки' },
  { id: 'monument', name: 'Памятники' },
  { id: 'park', name: 'Парки' }
];

const savedState = loadState();
const S = {
  mode: savedState.mode || 'travel',
  region: savedState.region || null,
  city: savedState.city || null,
  tags: new Set(savedState.tags || []),
  favs: new Set((savedState.favs || []).map(String)),
  route: Array.isArray(savedState.route) ? savedState.route : [],
  regions: [],
  cities: [],
  filtered: [],
  weather: null,
  loading: false
};

function loadState() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : {};
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

async function apiFetch(path, options = {}) {
  const response = await fetch(`${API}${path}`, {
    ...options,
    headers: {
      Accept: 'application/json',
      ...(options.body ? { 'Content-Type': 'application/json' } : {}),
      ...(options.headers || {})
    }
  });

  let data = null;
  try {
    data = await response.json();
  } catch (_) {
    // Empty/non-JSON response.
  }

  if (!response.ok) {
    const detail = data?.detail || `HTTP ${response.status}`;
    throw new Error(detail);
  }

  return data;
}

function getTelegramUserId() {
  const id = tg?.initDataUnsafe?.user?.id;
  return Number.isInteger(id) ? id : null;
}

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

  if (tg?.BackButton) {
    id === 'splash' ? tg.BackButton.hide() : tg.BackButton.show();
  }

  if (id === 'route') renderRoute();
  if (id === 'weather') renderWeatherScreen();
  if (!options.skipSave) saveState();
}

if (tg?.BackButton) {
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
  element._toastTimer = setTimeout(() => element.classList.remove('show'), 2200);
}

function showToast(message) { toast(message); }

function haptic(type = 'light') {
  if (tg?.HapticFeedback?.impactOccurred) tg.HapticFeedback.impactOccurred(type);
}

function updateFab() {
  const fab = document.getElementById('fab');
  const count = document.getElementById('fab-count');
  if (!fab || !count) return;
  count.textContent = S.route.length;
  fab.classList.toggle('hidden', S.route.length === 0);
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
  haptic();
}

function openWeather() {
  S.mode = 'weather';
  setActiveTab('weather');
  if (S.city && S.region) {
    go('weather');
    loadWeather(S.city);
  } else {
    go('regions');
  }
  haptic();
}

function bottomNavigate(tab) {
  if (tab === 'travel') openTravel();
  if (tab === 'weather') openWeather();
}

function renderRegions(list) {
  const grid = document.getElementById('regions-grid');
  if (!grid) return;
  if (!list.length) {
    grid.innerHTML = '<div style="padding:30px;text-align:center;color:var(--muted)">Регионы не найдены</div>';
    return;
  }
  grid.innerHTML = list.map(region => `
    <div class="card" onclick="pickRegion('${escapeAttr(region.id)}')">
      <span>${escapeHtml(region.name)}</span>
    </div>
  `).join('');
}

function filterRegions(query) {
  const q = String(query || '').toLowerCase().trim();
  renderRegions(S.regions.filter(region => region.name.toLowerCase().includes(q)));
}

async function loadRegions() {
  try {
    const regions = await apiFetch('/regions');
    S.regions = Array.isArray(regions) ? regions : [];
    renderRegions(S.regions);
  } catch (error) {
    console.error('Failed to load regions:', error);
    toast(`Не удалось загрузить регионы: ${error.message}`);
  }
}

async function pickRegion(id) {
  const region = S.regions.find(item => item.id === id);
  if (!region) return;

  S.region = region.id;
  S.city = null;
  S.cities = [];

  const title = document.getElementById('region-title');
  if (title) title.textContent = `${region.name} область`;

  const grid = document.getElementById('cities-grid');
  if (grid) grid.innerHTML = '<div style="padding:30px;text-align:center;color:var(--muted)">Загрузка городов…</div>';
  go('cities');

  try {
    S.cities = await apiFetch(`/cities/${encodeURIComponent(id)}`);
    renderCities(S.cities || []);
  } catch (error) {
    console.error('Failed to load cities:', error);
    if (grid) grid.innerHTML = `<div style="padding:30px;text-align:center;color:var(--muted)">${escapeHtml(error.message)}</div>`;
    toast(`Не удалось загрузить города: ${error.message}`);
  }
}

function renderCities(list) {
  const grid = document.getElementById('cities-grid');
  if (!grid) return;
  if (!list.length) {
    grid.innerHTML = '<div style="padding:30px;text-align:center;color:var(--muted)">Города не найдены</div>';
    return;
  }
  grid.innerHTML = list.map((city, index) => `
    <div class="card ${S.city === city.name ? 'active' : ''}" onclick="pickCity('${escapeAttr(city.name)}', ${index})">
      <span>${escapeHtml(city.name)}</span>
    </div>
  `).join('');
}

function filterCities(query) {
  const q = String(query || '').toLowerCase().trim();
  renderCities(S.cities.filter(city => city.name.toLowerCase().includes(q)));
}

async function pickCity(name, index) {
  const city = S.cities[index] || S.cities.find(item => item.name === name);
  if (!city) return;

  S.city = city.name;

  if (S.mode === 'weather') {
    go('weather');
    await loadWeather(S.city);
    return;
  }

  S.mode = 'travel';
  renderTags();
  go('tags');
  haptic();
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

  empty.style.display = 'none';
  box.style.display = 'block';
  if (S.weather?.city === S.city) renderWeather(S.weather);
  else loadWeather(S.city);
}

async function loadWeather(city) {
  const box = document.getElementById('weather-box');
  if (box) {
    box.style.display = 'block';
    box.innerHTML = '<div style="padding:30px;text-align:center;color:var(--muted)">Загрузка погоды…</div>';
  }

  try {
    S.weather = await apiFetch(`/weather/${encodeURIComponent(city)}`);
    renderWeather(S.weather);
  } catch (error) {
    console.error('Failed to load weather:', error);
    if (box) box.innerHTML = `<div style="padding:30px;text-align:center;color:var(--muted)">Не удалось загрузить погоду</div>`;
    toast(`Погода недоступна: ${error.message}`);
  }
}

function renderWeather(weather) {
  const box = document.getElementById('weather-box');
  if (!box || !weather) return;

  const details = [];
  if (weather.humidity != null) details.push(`<div><span>Влажность</span><strong>${weather.humidity}%</strong></div>`);
  if (weather.wind_speed != null) details.push(`<div><span>Ветер</span><strong>${weather.wind_speed} м/с</strong></div>`);
  if (weather.pressure != null) details.push(`<div><span>Давление</span><strong>${weather.pressure} hPa</strong></div>`);

  box.innerHTML = `
    <div class="weather-card">
      <div class="weather-city">${escapeHtml(weather.city || S.city || '')}</div>
      <div class="weather-main">
        <div class="weather-temp">${weather.temp != null ? `${weather.temp}°` : '—'}</div>
        <div class="weather-desc">${escapeHtml(weather.description || 'Нет данных')}</div>
      </div>
      ${details.length ? `<div class="weather-details">${details.join('')}</div>` : ''}
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
    <button type="button" class="tag ${S.tags.has(tag.id) ? 'active' : ''}" onclick="toggleTag('${escapeAttr(tag.id)}')">
      ${escapeHtml(tag.name)}
    </button>
  `).join('');

  if (button) button.disabled = S.tags.size === 0;
}

function toggleTag(id) {
  S.tags.has(id) ? S.tags.delete(id) : S.tags.add(id);
  renderTags();
  saveState();
  haptic();
}

async function loadCards() {
  if (!S.region || !S.city) {
    toast('Сначала выберите регион и город');
    return;
  }
  if (S.tags.size === 0) {
    toast('Выберите хотя бы одну категорию');
    return;
  }

  const feed = document.getElementById('feed');
  if (feed) feed.innerHTML = '<div style="padding:50px;text-align:center;color:var(--muted)">Загрузка мест…</div>';
  go('cards');

  try {
    const data = await apiFetch('/pois/query', {
      method: 'POST',
      body: JSON.stringify({
        region: S.region,
        city: S.city,
        tags: [...S.tags],
        limit: 30,
        offset: 0
      })
    });

    S.filtered = Array.isArray(data?.pois) ? data.pois : [];
    const title = document.getElementById('cards-title');
    if (title) title.textContent = S.city || 'Места';
    renderFeed();
  } catch (error) {
    console.error('Failed to load POIs:', error);
    S.filtered = [];
    if (feed) feed.innerHTML = `<div style="text-align:center;padding:50px;color:var(--muted)">Не удалось загрузить места<br><small>${escapeHtml(error.message)}</small></div>`;
    toast(`Места недоступны: ${error.message}`);
  }
}

function renderFeed() {
  const feed = document.getElementById('feed');
  if (!feed) return;

  if (S.filtered.length === 0) {
    feed.innerHTML = '<div style="text-align:center;padding:50px;color:var(--muted)">Ничего не найдено</div>';
    return;
  }

  feed.innerHTML = S.filtered.map(place => {
    const id = String(place.id);
    const isFavorite = S.favs.has(id);
    const inRoute = S.route.some(item => String(item.id) === id);
    const image = place.images?.medium || place.images?.thumb || place.image_url;

    return `
      <div class="poi-card">
        <div class="poi-img">
          ${image ? `<img src="${escapeAttr(image)}" alt="${escapeAttr(place.name)}" loading="lazy">` : `
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1">
              <path d="M3 21h18 M5 21V7l8-4 8 4v14 M9 21v-6h6v6"/>
            </svg>
          `}
        </div>
        <div class="poi-body">
          <div class="poi-name">${escapeHtml(place.name)}</div>
          <div class="poi-loc">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 2 C8 2 5 5 5 9 c0 5 7 13 7 13 s7-8 7-13 c0-4-3-7-7-7z"/>
              <circle cx="12" cy="9" r="2.5"/>
            </svg>
            ${escapeHtml(place.city || '')}
          </div>
          ${place.address ? `<div class="poi-loc">${escapeHtml(place.address)}</div>` : ''}
          <div class="poi-actions">
            <button class="poi-act ${isFavorite ? 'active' : ''}" type="button" onclick="toggleFav('${escapeAttr(id)}')">
              <svg viewBox="0 0 24 24" fill="${isFavorite ? 'currentColor' : 'none'}" stroke="currentColor" stroke-width="2">
                <path d="M20.84 4.61 a5.5 5.5 0 0 0-7.78 0 L12 5.67 l-1.06-1.06 a5.5 5.5 0 0 0-7.78 7.78 l1.06 1.06 L12 21.23 l7.78-7.78 1.06-1.06 a5.5 5.5 0 0 0 0-7.78z"/>
              </svg>
              Favorite
            </button>
            <button class="poi-act ${inRoute ? 'active' : ''}" type="button" onclick="toggleRoute('${escapeAttr(id)}')">
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

async function toggleFav(id) {
  const userId = getTelegramUserId();
  if (!userId) {
    toast('Откройте приложение через Telegram для избранного');
    return;
  }

  try {
    const data = await apiFetch('/favorites/toggle', {
      method: 'POST',
      body: JSON.stringify({ user_id: userId, poi_id: String(id) })
    });

    if (data?.favorited) S.favs.add(String(id));
    else S.favs.delete(String(id));

    toast(data?.favorited ? 'В избранном' : 'Удалено из избранного');
    renderFeed();
    saveState();
    haptic();
  } catch (error) {
    console.error('Favorite error:', error);
    toast(`Не удалось изменить избранное: ${error.message}`);
  }
}

async function loadFavorites() {
  const userId = getTelegramUserId();
  if (!userId) return;

  try {
    const data = await apiFetch(`/favorites/${userId}`);
    S.favs = new Set((data?.favorites || []).map(item => String(item.place_id)));
    saveState();
  } catch (error) {
    console.warn('Failed to load favorites:', error);
  }
}

function toggleRoute(id) {
  const key = String(id);
  const existing = S.route.find(item => String(item.id) === key);

  if (existing) {
    S.route = S.route.filter(item => String(item.id) !== key);
    toast('Удалено из маршрута');
  } else {
    const place = S.filtered.find(item => String(item.id) === key);
    if (place) {
      S.route.push(place);
      toast('Добавлено в маршрут');
    }
  }

  updateFab();
  renderFeed();
  saveState();
  haptic();
}

function goBackFromRoute() {
  S.filtered.length ? go('cards') : go('tags');
}

function renderRoute() {
  const list = document.getElementById('route-list');
  const button = document.getElementById('btn-build');
  if (!list || !button) return;

  if (!S.route.length) {
    list.innerHTML = '<div class="route-empty">Маршрут пуст.<br>Добавьте точки из карточек.</div>';
    button.disabled = true;
    return;
  }

  button.disabled = S.route.length < 2;
  list.innerHTML = S.route.map((place, index) => `
    <div class="route-item">
      <div class="route-num">${index + 1}</div>
      <div class="route-info">
        <div class="route-name">${escapeHtml(place.name)}</div>
        <div class="route-city">${escapeHtml(place.city || '')}</div>
      </div>
      <button class="route-del" type="button" onclick="removeRoute('${escapeAttr(String(place.id))}')">✕</button>
    </div>
  `).join('');
}

function removeRoute(id) {
  S.route = S.route.filter(item => String(item.id) !== String(id));
  updateFab();
  renderRoute();
  saveState();
}

async function buildRoute() {
  if (S.route.length < 2) {
    toast('Добавьте минимум 2 точки');
    return;
  }

  const button = document.getElementById('btn-build');
  if (button) button.disabled = true;

  try {
    const data = await apiFetch('/route/build', {
      method: 'POST',
      body: JSON.stringify({
        poi_ids: S.route.map(place => String(place.id)),
        optimize: true
      })
    });

    const byId = new Map(S.route.map(place => [String(place.id), place]));
    S.route = (data.poi_ids || []).map(id => byId.get(String(id))).filter(Boolean);
    renderRoute();
    saveState();

    if (data.google_maps_url) {
      toast(data.total_distance_km != null
        ? `Маршрут: ${data.total_distance_km} км`
        : 'Маршрут построен');
      window.open(data.google_maps_url, '_blank', 'noopener,noreferrer');
    } else {
      toast('Маршрут построен');
    }

    if (tg?.HapticFeedback?.notificationOccurred) {
      tg.HapticFeedback.notificationOccurred('success');
    }
  } catch (error) {
    console.error('Route build error:', error);
    toast(`Не удалось построить маршрут: ${error.message}`);
  } finally {
    if (button) button.disabled = S.route.length < 2;
  }
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
  haptic();
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
  haptic();
}

function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
}

function escapeAttr(value) {
  return escapeHtml(value).replaceAll('`', '&#096;');
}

async function init() {
  renderTags();
  updateFab();
  applyTheme(localStorage.getItem('jarvis-theme') || 'dark', false);
  applyLanguage(localStorage.getItem('jarvis-language') || 'BY', false);
  prepareWeatherButton();

  setActiveTab(S.mode === 'weather' ? 'weather' : 'travel');
  go('splash', { skipSave: true });

  await Promise.all([loadRegions(), loadFavorites()]);

  if (S.region) {
    const region = S.regions.find(item => item.id === S.region);
    if (region) {
      const title = document.getElementById('region-title');
      if (title) title.textContent = `${region.name} область`;
      try {
        S.cities = await apiFetch(`/cities/${encodeURIComponent(S.region)}`);
        renderCities(S.cities || []);
      } catch (error) {
        console.warn('Failed to restore cities:', error);
      }
    }
  }

  const savedScreen = savedState.screen;
  if (savedScreen && document.getElementById(savedScreen)) {
    if (['cities', 'tags', 'cards', 'weather'].includes(savedScreen) && (!S.region || !S.city) && savedScreen !== 'cities') {
      go('regions', { skipSave: true });
      return;
    }

    go(savedScreen, { skipSave: true });
    if (savedScreen === 'weather' && S.city) loadWeather(S.city);
    if (savedScreen === 'cards' && S.region && S.city && S.tags.size) loadCards();
  }
}

init();