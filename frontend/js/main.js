import { tg, state, persist, clearAppCache } from './core/state.js';
import { $ } from './ui/helpers.js';
import { applyTheme, toggleTheme } from './ui/theme.js';
import { applyLanguage, toggleLanguage } from './ui/language.js';
import { go, initTelegramBackButton, bindNavigation } from './core/router.js';
import { loadRegions, pickRegion, pickCity, toggleTag, filterRegions, filterCities, renderTags, startPlaces } from './features/travel.js?v=20260907-4';
import { loadWeather, renderWeather } from './features/weather.js';
import { loadFavorites, toggleFavorite, toggleRoute, openDetail, loadPage, updateFab, searchPlaces, shufflePlaces } from './features/places.js';
import { renderRoute, removeRoute, buildRoute, copyRoute, openRoute } from './features/route.js';
import { installExtraNavigation } from './features/navigation-extra.js';

if(tg){try{tg.ready();tg.expand();}catch(_) {}}

function handleClick(event){
 const el=event.target.closest('[data-action]');
 if(!el||!document.body.contains(el))return;
 const action=el.dataset.action;
 if(action==='theme'){event.preventDefault();event.stopPropagation();toggleTheme();persist();return}
 if(action==='language'){event.preventDefault();toggleLanguage();return}
 if(action==='start'){event.preventDefault();go('regions');loadRegions();return}
 if(action==='back'){event.preventDefault();go(el.dataset.screen||'regions');return}
 if(action==='region'){pickRegion(el.dataset.id);return}
 if(action==='city'){event.preventDefault();pickCity(el.dataset.city);return}
 if(action==='tag'){toggleTag(el.dataset.id);return}
 if(action==='show-places'){startPlaces();return}
 if(action==='choose-city'){state.mode='weather';go('regions');return}
 if(action==='weather-refresh'){loadWeather();return}
 if(action==='page-prev'||action==='page-next'){event.preventDefault();loadPage(Number(el.dataset.page));return}
 if(action==='shuffle'){event.preventDefault();shufflePlaces();return}
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
 if(event.target.matches('#region-search'))filterRegions(event.target.value);
 if(event.target.matches('#city-search'))filterCities(event.target.value);
 if(event.target.matches('#poi-search'))searchPlaces(event.target.value);
}
function bind(){
 document.addEventListener('click',handleClick);
 document.addEventListener('input',handleInput);
 $('#fab')?.addEventListener('click',()=>{go('route');renderRoute()});
 $('#bottom-nav')?.addEventListener('click',e=>{if(e.target.closest('[data-tab="weather"]')&&state.city&&state.region)loadWeather();});
 window.addEventListener('jarvis:weather',()=>loadWeather());
 window.addEventListener('jarvis:language',()=>{renderTags();if(state.weather)renderWeather();loadRegions();});
 window.addEventListener('jarvis:favorites-changed',()=>loadFavorites());
 bindNavigation();initTelegramBackButton();installExtraNavigation();

 // Telegram WebApp has no reliable close event. pagehide is the browser lifecycle
 // event closest to WebApp disposal; clear only persisted session/cache data there.
 window.addEventListener('pagehide',()=>clearAppCache(),{capture:true});
}
async function init(){
 bind();applyTheme(localStorage.getItem('jarvis-theme')||'dark',false);applyLanguage(localStorage.getItem('jarvis-language')||'RU',false);renderTags();updateFab();go('splash',{save:false});
 await Promise.all([loadRegions(),loadFavorites()]);
 if(state.region){try{const {request}=await import('./core/api.js');state.cities=await request(`/cities/${encodeURIComponent(state.region)}`)||[];}catch(_) {}}
 persist();
}
init().catch(error=>console.error('JARVIS init failed',error));
