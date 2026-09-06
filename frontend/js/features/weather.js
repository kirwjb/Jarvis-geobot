import { state } from '../core/state.js';
import { request } from '../core/api.js';
import { $, esc, toast } from '../ui/helpers.js';
import { t } from '../ui/language.js';

function weatherIcon(description='') {
  const text=description.toLowerCase();
  if(text.includes('гроза')||text.includes('гром'))return '⛈️';
  if(text.includes('снег')||text.includes('snow'))return '🌨️';
  if(text.includes('дожд')||text.includes('rain'))return '🌧️';
  if(text.includes('облач')||text.includes('cloud'))return '☁️';
  if(text.includes('туман')||text.includes('fog'))return '🌫️';
  return '☀️';
}

export async function loadWeather(city=state.city){
  const box=$('#weather-box'), empty=$('#weather-empty');
  if(empty)empty.style.display='none';
  if(box){box.style.display='block';box.innerHTML=`<div class="weather-shell"><div class="loading">${esc(t('weather_loading'))}</div></div>`;}
  if(!city){if(empty)empty.style.display='flex';return;}
  try{state.weather=await request(`/weather/${encodeURIComponent(city)}`);renderWeather();}
  catch(e){if(box)box.innerHTML=`<div class="weather-shell"><div class="empty">${esc(t('weather_failed'))}</div></div>`;toast(`${t('weather_failed')}: ${e.message}`)}
}

export function renderWeather(){
  const w=state.weather,box=$('#weather-box');if(!box||!w)return;
  const city=w.city||state.city||'',desc=w.description||'Нет данных';
  box.style.display='block';
  box.innerHTML=`<div class="weather-shell">
    <div class="weather-head">
      <div class="weather-place"><div class="weather-place-label">${esc(t('weather'))}</div><div class="weather-city">${esc(city)}</div></div>
      <button class="weather-refresh" type="button" data-action="weather-refresh" aria-label="↻">↻</button>
    </div>
    <div class="weather-hero"><div class="weather-symbol">${weatherIcon(desc)}</div><div><div class="weather-temperature">${w.temp!=null?`${esc(String(Math.round(w.temp)))}°`:'—'}</div><div class="weather-condition">${esc(desc)}</div></div></div>
    <div class="weather-metrics">
      <div class="weather-metric"><div class="weather-metric-icon">💧</div><span class="weather-metric-label">${esc(t('humidity'))}</span><strong class="weather-metric-value">${w.humidity!=null?`${esc(String(w.humidity))}%`:'—'}</strong></div>
      <div class="weather-metric"><div class="weather-metric-icon">💨</div><span class="weather-metric-label">${esc(t('wind'))}</span><strong class="weather-metric-value">${w.wind_speed!=null?`${esc(String(w.wind_speed))} м/с`:'—'}</strong></div>
      <div class="weather-metric"><div class="weather-metric-icon">◉</div><span class="weather-metric-label">${esc(t('pressure'))}</span><strong class="weather-metric-value">${w.pressure!=null?`${esc(String(w.pressure))} hPa`:'—'}</strong></div>
    </div>
    <div class="weather-updated">${w.cached?'JARVIS использует свежий кэш':'JARVIS обновил данные сейчас'}</div>
  </div>`;
}
