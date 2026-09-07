import { tg, state, persist, clearAppCache } from './core/state.js';
import { $ } from './ui/helpers.js';
import { applyTheme, toggleTheme } from './ui/theme.js';
import { applyLanguage, toggleLanguage } from './ui/language.js';
import { go, initTelegramBackButton, bindNavigation } from './core/router.js';
import { loadRegions, pickRegion, pickCity, toggleTag, filterRegions, filterCities, renderTags, startPlaces } from './features/travel.js?v=20260907-4';
import { loadWeather, renderWeather } from './features/weather.js';
import { loadFavorites, toggleFavorite, toggleRoute, openDetail, loadPage, updateFab, searchPlaces, shufflePlaces } from './features/places.js?v=20260907-2';
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
 if(action==='region'){event.preventDefault();pickRegion(el.dataset.id);return}
 if(action==='city'){event.preventDefault();pickCity(el.dataset.city);return}
 if(action==='tag'){event.preventDefault();toggleTag(el.dataset.id);return}
 if(action==='show-places'||action==='start-places'){event.preventDefault();startPlaces();return}
 if(action==='page-prev'||action==='page-next'){event.preventDefault();loadPage(Number(el.dataset.page));return}
 if(action==='shuffle'){event.preventDefault();shufflePlaces();return}
 if(action==='favorite'){event.preventDefault();toggleFavorite(el.dataset.id);return}
 if(action==='route'){event.preventDefault();toggleRoute(el.dataset.id);return}
 if(action==='detail'){event.preventDefault();openDetail(el.dataset.id);return}
 if(action==='close-modal'){event.preventDefault();el.closest('.jarvis-modal')?.remove();return}
 if(action==='back'){event.preventDefault();window.history.back();return}
}

document.addEventListener('click',handleClick);
document.addEventListener('input',event=>{if(event.target.id==='poi-search')searchPlaces(event.target.value);if(event.target.id==='region-search')filterRegions(event.target.value);if(event.target.id==='city-search')filterCities(event.target.value);});
window.addEventListener('pagehide',()=>clearAppCache(),{capture:true});

async function init(){bindNavigation();applyTheme(localStorage.getItem('jarvis-theme')||'dark',false);applyLanguage(localStorage.getItem('jarvis-language')||'RU',false);renderTags();updateFab();go('splash',{save:false});await Promise.all([loadRegions(),loadFavorites()]);if(state.region){try{state.cities=await import('./core/api.js').then(({request})=>request(`/cities/${encodeURIComponent(state.region)}`)||[]);}catch(_) {}}persist();}
init().catch(error=>console.error('JARVIS init failed',error));
