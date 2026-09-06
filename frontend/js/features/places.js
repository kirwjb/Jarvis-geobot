import { state, persist, telegramUserId } from '../core/state.js';
import { request } from '../core/api.js';
import { $, esc, toast, haptic } from '../ui/helpers.js';
import { go } from '../core/router.js';
import { t } from '../ui/language.js';

const PAGE=8; let page=0, hasNext=false, loading=false, key=''; const cache=new Map();
const queryKey=()=>JSON.stringify({region:state.region,city:state.city,tags:[...state.tags].sort()});

export function poiCardMarkup(p){
 const id=String(p.id),im=p.images?.medium||p.images?.thumb||p.image_url,fav=state.favs.has(id),rt=state.route.some(x=>String(x.id)===id);
 return `<article class="poi-card" data-action="detail" data-id="${esc(id)}"><div class="poi-img">${im?`<img src="${esc(im)}" alt="${esc(p.name)}" loading="lazy" decoding="async">`:'<div class="poi-placeholder">🏛️</div>'}</div><div class="poi-body"><div class="poi-name">${esc(p.name||t('place'))}</div><div class="poi-loc">📍 ${esc(p.city||'')}${p.address?` · ${esc(p.address)}`:''}</div><div class="poi-actions"><button class="poi-act ${fav?'active':''}" type="button" data-action="favorite" data-id="${esc(id)}">${fav?'❤️':'♡'} ${esc(t('favorite'))}</button><button class="poi-act ${rt?'active':''}" type="button" data-action="route" data-id="${esc(id)}">${rt?'✓':'＋'} ${esc(t('route_add'))}</button></div></div></article>`;
}
function render(){const feed=$('#feed');if(!feed)return;feed.innerHTML=state.pois.length?state.pois.map(poiCardMarkup).join(''):`<div class="empty">${esc(t('nothing'))}</div>`;const box=$('#poi-pagination');if(box)box.innerHTML=(state.pois.length||hasNext)?`<button class="poi-page-btn" type="button" data-action="page-prev" data-page="${page-1}" ${page===0||loading?'disabled':''}>←</button><span class="poi-page-label">${esc(t('page'))} ${page+1}</span><button class="poi-page-btn" type="button" data-action="page-next" data-page="${page+1}" ${!hasNext||loading?'disabled':''}>→</button>`:'';}
const loadingMarkup=()=>`<div class="jarvis-loading"><div class="jarvis-spinner"></div><div class="jarvis-loading-title">${esc(t('searching'))}</div></div>`;
export async function loadPlaces(){go('cards');page=0;cache.clear();key=queryKey();state.pois=[];$('#feed').innerHTML=loadingMarkup();$('#cards-title').textContent=state.city||t('places');await loadPage(0);}

function filterDbPlaces(items){
 const wanted=[...state.tags].map(x=>String(x).toLowerCase());
 if(!wanted.length)return items;
 return items.filter(p=>wanted.some(tag=>String(p.category||'').toLowerCase()===tag||String(p.category||'').toLowerCase().includes(tag)||tag==='architecture'&&['castle','church','monument','manor','gallery','ruins'].includes(p.category)||tag==='nature'&&['park','viewpoint','ruins'].includes(p.category)));
}

export async function loadPage(next){
 if(next<0||loading)return;
 const k=queryKey();if(k!==key){cache.clear();key=k;page=0}
 if(cache.has(next)){const c=cache.get(next);page=next;state.pois=c.places;hasNext=c.hasNext;render();return}
 loading=true;$('#feed').innerHTML=loadingMarkup();
 try{
   let pois=[];
   // 1) Search the application database by city first. This also tolerates old region naming.
   if(next===0&&state.city){
     const db=await request(`/pois?city=${encodeURIComponent(state.city)}&limit=30&offset=0`);
     pois=filterDbPlaces(Array.isArray(db?.pois)?db.pois:[]);
   }
   // 2) If DB has no matching attractions, ask the POI query endpoint to hydrate from OSM and cache them.
   if(!pois.length){
     const d=await request('/pois/query',{method:'POST',body:JSON.stringify({region:state.region,city:state.city,tags:[...state.tags],limit:PAGE+1,offset:next*PAGE})});
     pois=Array.isArray(d?.pois)?d.pois:[];
   }
   const c={places:pois.slice(0,PAGE),hasNext:pois.length>PAGE};cache.set(next,c);page=next;state.pois=c.places;hasNext=c.hasNext;render();
 }catch(e){toast(`${t('places_failed')}: ${e.message}`)}finally{loading=false;render();}
}

export async function toggleFavorite(id){if(!telegramUserId())return toast(t('tg_only'));try{const d=await request('/favorites/toggle',{method:'POST',body:JSON.stringify({poi_id:String(id)})});d?.favorited?state.favs.add(String(id)):state.favs.delete(String(id));render();persist();haptic();window.dispatchEvent(new CustomEvent('jarvis:favorites-changed'));}catch(e){toast(`Не удалось изменить избранное: ${e.message}`)}}
export function toggleRoute(id){const k=String(id),found=state.route.find(x=>String(x.id)===k);if(found)state.route=state.route.filter(x=>String(x.id)!==k);else{const p=state.pois.find(x=>String(x.id)===k);if(p)state.route.push(p)}updateFab();render();persist();haptic();}
export function updateFab(){const fab=$('#fab'),count=$('#fab-count');if(!fab)return;fab.classList.toggle('hidden',!state.route.length);if(count)count.textContent=state.route.length;}
export async function openDetail(id){try{const p=await request(`/pois/${encodeURIComponent(id)}`),im=p.images?.large||p.images?.medium||p.images?.thumb||p.image_url,modal=document.createElement('div');modal.className='jarvis-modal';modal.innerHTML=`<div class="jarvis-modal-card"><button class="jarvis-close" type="button" data-action="close-modal">×</button>${im?`<img class="jarvis-detail-image" src="${esc(im)}" alt="${esc(p.name)}" decoding="async">`:'<div class="poi-placeholder">🏛️</div>'}<h2>${esc(p.name||t('place'))}</h2><p>📍 ${esc(p.city||'')}${p.address?`<br>🏠 ${esc(p.address)}`:''}</p><div class="jarvis-modal-actions"><button class="btn-main" type="button" data-action="favorite" data-id="${esc(String(p.id))}">♡ ${esc(t('favorite'))}</button><button class="btn-route" type="button" data-action="route" data-id="${esc(String(p.id))}">＋ ${esc(t('route_add'))}</button></div></div>`;modal.addEventListener('click',e=>{if(e.target===modal)modal.remove()});document.body.appendChild(modal);}catch(e){toast(`Не удалось загрузить место: ${e.message}`)}}
export async function loadFavorites(){if(!telegramUserId())return;try{const d=await request('/favorites/me');state.favs=new Set((d?.favorites||[]).map(x=>String(x.place_id)));persist();}catch(e){console.warn('favorites',e)}}
