import { state, TAGS, persist } from '../core/state.js';
import { request } from '../core/api.js';
import { $, esc, toast, haptic } from '../ui/helpers.js';
import { go } from '../core/router.js';
import { loadPlaces } from './places.js';
import { t } from '../ui/language.js';

export function renderRegions(list=state.regions){const grid=$('#regions-grid');if(!grid)return;grid.innerHTML=list.length?list.map(r=>`<button class="card" type="button" data-action="region" data-id="${esc(r.id)}"><span>${esc(r.name)}</span></button>`).join(''):`<div class="empty">${esc(t('nothing'))}</div>`;}
export function renderCities(list=state.cities){const grid=$('#cities-grid');if(!grid)return;grid.innerHTML=list.length?list.map(c=>`<button class="card ${state.city===c.name?'active':''}" type="button" data-action="city" data-city="${esc(c.name)}"><span>${esc(c.name)}</span></button>`).join(''):`<div class="empty">${esc(t('nothing'))}</div>`;}
export function renderTags(){
 const list=$('#tags-list');if(!list)return;
 list.innerHTML=TAGS.map(x=>`<button class="tag ${state.tags.has(x.id)?'active':''}" type="button" data-action="tag" data-id="${x.id}">${esc(t(x.id))}</button>`).join('');
 const btn=$('#btn-tags');if(btn)btn.disabled=!state.tags.size;
}
export async function loadRegions(){try{state.regions=await request('/regions')||[];renderRegions();}catch(e){console.error(e);toast(`${t('regions_failed')}: ${e.message}`);}}
export async function pickRegion(id){
 const region=state.regions.find(r=>r.id===id);if(!region)return;
 state.region=region.id;state.city=null;state.cities=[];
 $('#region-title').textContent=region.name;$('#cities-grid').innerHTML=`<div class="loading">${esc(t('loading'))}</div>`;go('cities');
 try{state.cities=await request(`/cities/${encodeURIComponent(id)}`)||[];renderCities();}catch(e){$('#cities-grid').innerHTML=`<div class="empty">${esc(e.message)}</div>`;toast(`${t('cities_failed')}: ${e.message}`);}persist();
}
export function pickCity(name){
 const wanted=String(name||'').trim();
 const city=state.cities.find(c=>c.name===wanted);
 if(!city)return;
 state.city=city.name;
 if(state.mode==='weather'){go('weather');window.dispatchEvent(new CustomEvent('jarvis:weather'));return;}
 renderTags();go('tags');persist();haptic();
}
export function toggleTag(id){state.tags.has(id)?state.tags.delete(id):state.tags.add(id);renderTags();persist();haptic();}
export function filterRegions(q){const x=String(q||'').toLowerCase().trim();renderRegions(state.regions.filter(r=>r.name.toLowerCase().includes(x)));}
export function filterCities(q){const x=String(q||'').toLowerCase().trim();renderCities(state.cities.filter(c=>c.name.toLowerCase().includes(x)));}
export async function startPlaces(){if(!state.region||!state.city)return toast(t('select_city'));if(!state.tags.size)return toast(t('select_category'));await loadPlaces();}
