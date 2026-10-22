import { state, persist } from '../core/state.js?v=20261017-010';
import { request } from '../core/api.js?v=20261017-010';
import { $, esc, toast, haptic } from '../ui/helpers.js?v=20261017-010';
import { t } from '../ui/language.js?v=20261017-010';
import { ICONS } from '../ui/icons.js?v=20261017-010';

export const POPULAR_CITIES = ['Минск', 'Брест', 'Гродно', 'Витебск', 'Могилев', 'Гомель', 'Бобруйск', 'Полоцк'];

export const ALL_BELARUS_CITIES = [
  'Минск', 'Брест', 'Гродно', 'Витебск', 'Могилев', 'Гомель',
  'Бобруйск', 'Барановичи', 'Борисов', 'Пинск', 'Орша', 'Мозырь',
  'Солигорск', 'Новополоцк', 'Лида', 'Молодечно', 'Полоцк', 'Жлобин',
  'Светлогорск', 'Речица', 'Кобрин', 'Слуцк', 'Волковыск', 'Слоним',
  'Сморгонь', 'Калинковичи', 'Рогачев', 'Горки', 'Осиповичи', 'Береза',
  'Несвиж', 'Заславль', 'Браслав', 'Мир'
];

export function stripEmojis(text) {
  if (!text) return '';
  return String(text)
    .replace(/[\u{1F300}-\u{1F9FF}\u{2600}-\u{27BF}\u{2300}-\u{23FF}\u{2B50}\u{2B55}\u{FE0F}]/gu, '')
    .trim();
}

function weatherIcon(description='', hourOverride=null) {
  const clean = stripEmojis(description);
  const text = (clean || '').toLowerCase();
  let hour;
  if (hourOverride !== null && hourOverride !== undefined && !isNaN(hourOverride)) {
    hour = Number(hourOverride) % 24;
  } else {
    const d = new Date();
    hour = (d.getUTCHours() + 3) % 24;
  }
  const isNight = hour >= 20 || hour < 6;
  const isTwilight = (hour >= 18 && hour < 20) || (hour >= 5 && hour < 6);

  if (text.includes('гроза') || text.includes('гром') || text.includes('thunder') || text.includes('навальніц')) return ICONS.weatherThunder;
  if (text.includes('снег') || text.includes('snow') || text.includes('снеж')) return ICONS.weatherSnow;
  if (text.includes('дожд') || text.includes('rain') || text.includes('морос') || text.includes('зліва') || text.includes('морась')) return ICONS.weatherRain;
  if (text.includes('туман') || text.includes('fog') || text.includes('mist')) return ICONS.weatherFog;

  if (text.includes('перемен') || text.includes('partly') || text.includes('местами') || text.includes('небольш') || text.includes('перамен')) {
    return isNight ? ICONS.weatherCloudMoon : ICONS.weatherCloudSun;
  }
  if (text.includes('облач') || text.includes('пасмур') || text.includes('cloud') || text.includes('хмарн') || text.includes('пахмур')) {
    return ICONS.weatherCloud;
  }
  if (text.includes('ясно') || text.includes('clear') || text.includes('ясна') || text.includes('сонеч') || text.includes('sunny')) {
    return isNight ? ICONS.weatherMoon : ICONS.weatherSun;
  }

  if (isNight) {
    return isTwilight ? ICONS.weatherTwilight : ICONS.weatherMoon;
  }
  return ICONS.weatherSun;
}

export function resolveWeatherCity(param) {
  if (typeof param === 'string' && param.trim()) {
    return param.trim();
  }
  if (param && typeof param === 'object' && param.detail?.city) {
    return String(param.detail.city).trim();
  }
  if (state.weatherCity && String(state.weatherCity).trim()) {
    return String(state.weatherCity).trim();
  }
  if (state.city && String(state.city).trim()) {
    return String(state.city).trim();
  }
  return 'Минск';
}

export function renderWeatherCityChips(activeCity = state.weatherCity) {
  const container = $('#weather-chips');
  if (!container) return;
  const current = (activeCity || state.weatherCity || state.city || 'Минск').toLowerCase().trim();
  container.innerHTML = POPULAR_CITIES.map(city => {
    const isActive = city.toLowerCase().trim() === current;
    return `<button class="weather-chip ${isActive ? 'active' : ''}" type="button" data-action="weather-city" data-city="${esc(city)}" aria-pressed="${isActive ? 'true' : 'false'}">${esc(city)}</button>`;
  }).join('');
}

export function selectWeatherCity(city) {
  const chosen = (city || '').trim();
  if (!chosen) return;
  state.weatherCity = chosen;
  persist();
  renderWeatherCityChips(chosen);
  closeWeatherDropdown();
  const searchInput = $('#weather-city-search');
  if (searchInput) searchInput.value = '';
  loadWeather(chosen);
}

export function filterWeatherCities(query) {
  const dropdown = $('#weather-city-dropdown');
  if (!dropdown) return;
  const q = String(query || '').trim().toLowerCase();
  if (!q) {
    dropdown.style.display = 'none';
    dropdown.innerHTML = '';
    return;
  }
  const matches = ALL_BELARUS_CITIES.filter(c => c.toLowerCase().includes(q));
  if (!matches.length) {
    dropdown.innerHTML = `<div class="weather-city-no-results">${esc(t('nothing'))}</div>`;
  } else {
    const current = (state.weatherCity || state.city || '').toLowerCase().trim();
    dropdown.innerHTML = matches.map(c => {
      const isActive = c.toLowerCase().trim() === current;
      return `<button class="weather-city-option ${isActive ? 'active' : ''}" type="button" data-action="weather-city" data-city="${esc(c)}"><span>${esc(c)}</span></button>`;
    }).join('');
  }
  dropdown.style.display = 'flex';
}

export function closeWeatherDropdown() {
  const dropdown = $('#weather-city-dropdown');
  if (dropdown) {
    dropdown.style.display = 'none';
    dropdown.innerHTML = '';
  }
}

export async function loadWeather(cityArg = null) {
  const city = resolveWeatherCity(cityArg);
  state.weatherCity = city;
  renderWeatherCityChips(city);

  const box = $('#weather-box');
  const empty = $('#weather-empty');
  const isMissing = !city || ['none', 'null', 'undefined', 'nan', ''].includes(city.toLowerCase());

  if (isMissing) {
    if (box) box.style.display = 'none';
    if (empty) empty.style.display = 'flex';
    return;
  }

  if (empty) empty.style.display = 'none';
  if (box) {
    box.style.display = 'block';
    box.innerHTML = `<div class="weather-shell weather-skeleton">
      <div class="weather-head">
        <div class="weather-place">
          <div class="sk-line sk-label"></div>
          <div class="sk-line sk-city"></div>
        </div>
        <div class="sk-btn"></div>
      </div>
      <div class="weather-hero">
        <div class="sk-symbol"></div>
        <div style="flex:1">
          <div class="sk-line sk-temp"></div>
          <div class="sk-line sk-cond"></div>
        </div>
      </div>
      <div class="weather-metrics">
        <div class="weather-metric sk-metric"></div>
        <div class="weather-metric sk-metric"></div>
        <div class="weather-metric sk-metric"></div>
      </div>
    </div>`;
  }

  try {
    state.weather = await request(`/weather/${encodeURIComponent(city)}`);
    if (state.weather && (!state.weather.temp && (!state.weather.city || ['none', 'null'].includes(state.weather.city.toLowerCase())))) {
      if (box) box.style.display = 'none';
      if (empty) empty.style.display = 'flex';
      return;
    }
    renderWeather();
  } catch (e) {
    if (box) box.innerHTML = `<div class="weather-shell"><div class="empty">${esc(t('weather_failed'))}</div></div>`;
    toast(`${t('weather_failed')}: ${e.message}`);
  }
}

export function renderWeather() {
  const w = state.weather;
  const box = $('#weather-box');
  if (!box || !w) return;
  const city = w.city || state.weatherCity || state.city || '';
  const desc = stripEmojis(w.description) || 'Нет данных';
  const feelsLike = w.feels_like != null ? `${esc(t('feels_like'))} ${esc(String(Math.round(w.feels_like)))}°` : '';
  const hourlyItems = Array.isArray(w.hourly) ? w.hourly : [];
  const forecastItems = Array.isArray(w.forecast) ? w.forecast : [];

  const hourlyHtml = hourlyItems.length ? `
    <div class="weather-hourly-wrap">
      <div class="weather-section-title">${esc(t('hourly'))}</div>
      <div class="weather-hourly-strip">
        ${hourlyItems.map(item => {
          const hourNum = parseInt(item.time, 10);
          const icon = weatherIcon(item.description, isNaN(hourNum) ? null : hourNum);
          const rain = item.chance_of_rain ?? item.chanceofrain;
          return `<div class="weather-hourly-item">
            <span class="weather-hourly-time">${esc(item.time)}</span>
            <span class="weather-hourly-icon">${icon}</span>
            <span class="weather-hourly-temp">${item.temp != null ? `${esc(String(Math.round(item.temp)))}°` : '—'}</span>
            ${rain && rain > 15 ? `<span class="weather-hourly-pop">${ICONS.weatherRain} ${esc(String(rain))}%</span>` : ''}
          </div>`;
        }).join('')}
      </div>
    </div>` : '';

  const sunHtml = (w.sunrise || w.sunset) ? `
    <div class="weather-sun">
      <div class="weather-sun-item">
        <span class="weather-sun-icon">${ICONS.sunrise}</span>
        <div>
          <span class="weather-sun-label">${esc(t('sunrise'))}</span>
          <strong class="weather-sun-value">${esc(w.sunrise || '—')}</strong>
        </div>
      </div>
      <div class="weather-sun-divider"></div>
      <div class="weather-sun-item">
        <span class="weather-sun-icon">${ICONS.sunset}</span>
        <div>
          <span class="weather-sun-label">${esc(t('sunset'))}</span>
          <strong class="weather-sun-value">${esc(w.sunset || '—')}</strong>
        </div>
      </div>
    </div>` : '';

  const forecastHtml = forecastItems.length ? `
    <div class="weather-forecast-wrap">
      <div class="weather-section-title">${esc(t('forecast_3days'))}</div>
      <div class="weather-forecast-grid">
        ${forecastItems.map(f => {
          const max = f.max_temp ?? f.maxtempC;
          const min = f.min_temp ?? f.mintempC;
          return `<div class="weather-forecast-item">
            <span class="weather-forecast-date">${esc(f.date)}</span>
            <span class="weather-forecast-temps">${max != null ? `${Math.round(max)}°` : '—'} <span class="weather-forecast-low">${min != null ? `/ ${Math.round(min)}°` : '—'}</span></span>
          </div>`;
        }).join('')}
      </div>
    </div>` : '';

  box.style.display = 'block';
  box.innerHTML = `<div class="weather-shell">
    <div class="weather-head">
      <div class="weather-place"><div class="weather-place-label">${esc(t('weather'))}</div><div class="weather-city">${esc(city)}</div></div>
      <button class="weather-refresh" type="button" data-action="weather-refresh" aria-label="Абнавіць">${ICONS.refresh}</button>
    </div>
    <div class="weather-hero">
      <div class="weather-symbol">${weatherIcon(desc)}</div>
      <div>
        <div class="weather-temperature">${w.temp != null ? `${esc(String(Math.round(w.temp)))}°` : '—'}</div>
        <div class="weather-condition">${esc(desc)}</div>
        ${feelsLike ? `<div class="weather-feels">${feelsLike}</div>` : ''}
      </div>
    </div>
    <div class="weather-metrics">
      <div class="weather-metric"><div class="weather-metric-icon">${ICONS.humidity}</div><span class="weather-metric-label">${esc(t('humidity'))}</span><strong class="weather-metric-value">${w.humidity != null ? `${esc(String(w.humidity))}%` : '—'}</strong></div>
      <div class="weather-metric"><div class="weather-metric-icon">${ICONS.wind}</div><span class="weather-metric-label">${esc(t('wind'))}</span><strong class="weather-metric-value">${w.wind_speed != null ? `${esc(String(w.wind_speed))} м/с` : '—'}</strong></div>
      <div class="weather-metric"><div class="weather-metric-icon">${ICONS.pressure}</div><span class="weather-metric-label">${esc(t('pressure'))}</span><strong class="weather-metric-value">${w.pressure != null ? `${esc(String(w.pressure))} hPa` : '—'}</strong></div>
    </div>
    ${hourlyHtml}
    ${sunHtml}
    ${forecastHtml}
    <div class="weather-updated">${esc(w.cached ? t('weather_cached') : t('weather_updated'))}</div>
  </div>`;
}
