import { state } from '../core/state.js';
import { request } from '../core/api.js';
import { $, esc, toast } from '../ui/helpers.js';

export async function loadWeather(city=state.city){
  const box=$('#weather-box'); if(box){box.style.display='block';box.innerHTML='<div class="loading">Загрузка погоды…</div>';}
  try{state.weather=await request(`/weather/${encodeURIComponent(city)}`);renderWeather();}
  catch(e){if(box)box.innerHTML='<div class="empty">Не удалось загрузить погоду</div>';toast(`Погода недоступна: ${e.message}`)}
}
export function renderWeather(){const w=state.weather,box=$('#weather-box');if(!box||!w)return;box.innerHTML=`<div class="weather-card"><div class="weather-city">${esc(w.city||state.city||'')}</div><div class="weather-main"><div class="weather-temp">${w.temp!=null?`${w.temp}°`:'—'}</div><div class="weather-desc">${esc(w.description||'Нет данных')}</div></div><div class="weather-details">${w.humidity!=null?`<div><span>Влажность</span><strong>${w.humidity}%</strong></div>`:''}${w.wind_speed!=null?`<div><span>Ветер</span><strong>${w.wind_speed} м/с</strong></div>`:''}${w.pressure!=null?`<div><span>Давление</span><strong>${w.pressure} hPa</strong></div>`:''}</div></div>`;}
