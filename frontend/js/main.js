import { tg, state, persist } from './core/state.js';
import { $, haptic } from './ui/helpers.js';
import { applyTheme, toggleTheme } from './ui/theme.js';
import { applyLanguage, toggleLanguage } from './ui/language.js';
import { go, initTelegramBackButton, bindNavigation } from './core/router.js';
import { loadRegions, pickRegion, pickCity, toggleTag, filterRegions, filterCities, renderTags, startPlaces } from './features/travel.js';
import { loadWeather } from './features/weather.js';
import { loadFavorites, toggleFavorite, toggleRoute, openDetail, loadPage, updateFab } from './features/places.js';
import { renderRoute, removeRoute, buildRoute, back, copyRoute, openRoute } from './features/route.js';

if(tg){try{tg.ready();tg.expand();}catch(_) {}}

function routeScreen(id){
  if(id==='route') renderRoute();
  if(id==='weather' && state.city) loadWeather();
}
function handleClick(event){
  const el=event.target.closest('[data-action]');
  if(!el || !document.body.contains(el)) return;
  const action=el.dataset.action;
  if(action==='theme'){event.preventDefault();toggleTheme();return}
  if(action==='language'){event.preventDefault();toggleLanguage();return}
  if(action==='start'){event.preventDefault();go('regions');loadRegions();return}
  if(action==='back'){event.preventDefault();go(el.dataset.screen||'regions');return}
  if(action==='region'){pickRegion(el.dataset.id);return}
  if(action==='city'){pickCity(Number(el.dataset.index));return}
  if(action==='tag'){toggleTag(el.dataset.id);return}
  if(action==='show-places'){startPlaces();return}
  if(action==='page-prev'){loadPage(Number(el.dataset.page)-1);return}
  if(action==='page-next'){loadPage(Number(el.dataset.page)+1);return}
  if(action==='favorite'){event.stopPropagation();toggleFavorite(el.dataset.id);return}
  if(action==='route'){event.stopPropagation();toggleRoute(el.dataset.id);return}
  if(action==='detail'){openDetail(el.dataset.id);return}
  if(action==='remove-route'){removeRoute(el.dataset.id);return}
  if(action==='build-route'){buildRoute();return}
  if(action==='open-route'){openRoute(el.dataset.url);return}
  if(action==='copy-route'){copyRoute(el.dataset.url);return}
  if(action==='close-modal'){el.closest('.jarvis-modal')?.remove();return}
}
function handleInput(event){
  if(event.target.matches('#region-search')) filterRegions(event.target.value);
  if(event.target.matches('#city-search')) filterCities(event.target.value);
}

function bind(){
  document.addEventListener('click',handleClick);
  document.addEventListener('input',handleInput);
  $('#weather')?.addEventListener('click',e=>{if(e.target.closest('[data-action="choose-city"]')){state.mode='weather';go('regions');}});
  window.addEventListener('jarvis:weather',()=>loadWeather());
  $('#fab')?.addEventListener('click',()=>{go('route');renderRoute()});
  bindNavigation(); initTelegramBackButton();
}

async function init(){
  bind();
  applyTheme(localStorage.getItem('jarvis-theme')||'dark',false);
  applyLanguage(localStorage.getItem('jarvis-language')||'RU',false);
  renderTags(); updateFab(); go('splash',{save:false});
  await Promise.all([loadRegions(),loadFavorites()]);
  if(state.region){
    try{state.cities=await (await import('./core/api.js')).request(`/cities/${encodeURIComponent(state.region)}`)||[];}catch(_){}
  }
  // Deliberately restore only data, never an old screen. Navigation starts from splash.
  persist();
}

init().catch(error=>{console.error('JARVIS init failed',error);});
