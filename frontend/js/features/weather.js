import { state } from '../core/state.js?v=1791475344';
import { request } from '../core/api.js?v=1791475344';
import { $, esc, toast } from '../ui/helpers.js?v=1791475344';
import { t } from '../ui/language.js?v=1791475344';

function weatherIcon(description='') {
  const text = description.toLowerCase();
  
  // Calculate hour in Minsk (UTC+3) regardless of local browser timezone
  const d = new Date();
  const hour = (d.getUTCHours() + 3) % 24;
  
  const isNight = hour >= 19 || hour < 6;
  const isTwilight = hour >= 18 && hour <= 19 || hour >= 5 && hour <= 6;

  if (text.includes('гроза') || text.includes('гром')) return '⛈️';
  if (text.includes('снег') || text.includes('snow')) return '🌨️';
  if (text.includes('дожд') || text.includes('rain') || text.includes('морос')) return '🌧️';
  if (text.includes('туман') || text.includes('fog')) return '🌫️';
  
  if (text.includes('перемен') || text.includes('partly') || text.includes('местами') || text.includes('небольш')) {
    return isNight ? '☁️' : '⛅';
  }
  if (text.includes('облач') || text.includes('пасмур') || text.includes('cloud')) {
    return '☁️';
  }
  if (text.includes('ясно') || text.includes('clear')) {
    return isNight ? '🌙' : '☀️';
  }
  
  if (isNight) {
    return isTwilight ? '🌗' : '🌙';
  }
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
