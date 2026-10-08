import { state, persist, tg } from '../core/state.js?v=1791475344';
import { request } from '../core/api.js?v=1791475344';
import { $, esc, toast, haptic } from '../ui/helpers.js?v=1791475344';
import { go } from '../core/router.js?v=1791475344';
import { t } from '../ui/language.js?v=1791475344';

/** Update the floating route button state and counter based on current route points. */
export function updateRouteFab() {
  const fab = $('#fab');
  if (!fab) return;
  fab.classList.toggle('hidden', !state.route.length);
  const count = $('#fab-count');
  if (count) count.textContent = state.route.length;
}
export const updateFab = updateRouteFab;

/** Add or remove a place from the route and update route indicators. */
export function toggleRoute(id) {
  const key = String(id);
  const exists = state.route.some((item) => String(item.id) === key);
  if (exists) {
    state.route = state.route.filter((item) => String(item.id) !== key);
  } else {
    const place = state.pois.find((item) => String(item.id) === key);
    if (place) state.route.push(place);
  }
  updateRouteFab();
  persist();
  haptic();
  window.dispatchEvent(new CustomEvent('jarvis:route-changed', { detail: { id: key } }));
}

export function renderRoute() {
  const list = $('#route-list'), btn = $('#btn-build');
  if (!list || !btn) return;
  if (!state.route.length) {
    list.innerHTML = `<div class="route-empty">${esc(t('route_empty'))}</div>`;
    btn.disabled = true;
    return;
  }
  btn.disabled = state.route.length < 2;
  list.innerHTML = state.route.map((p, i) => `<div class="route-item"><div class="route-num">${i + 1}</div><div class="route-info"><div class="route-name">${esc(p.name)}</div><div class="route-city">${esc(p.city || '')}</div></div><button class="route-del" type="button" data-action="remove-route" data-id="${esc(String(p.id))}">✕</button></div>`).join('');
}

export function removeRoute(id) {
  state.route = state.route.filter((p) => String(p.id) !== String(id));
  updateRouteFab();
  renderRoute();
  persist();
  window.dispatchEvent(new CustomEvent('jarvis:route-changed', { detail: { id: String(id) } }));
}
export async function buildRoute(){
 if(state.route.length<2)return toast('Добавьте минимум 2 точки');
 const btn=$('#btn-build');if(btn)btn.disabled=true;
 try{
  const d=await request('/route/build',{method:'POST',body:JSON.stringify({poi_ids:state.route.map(p=>String(p.id)),optimize:true})});
  const names=state.route.map((p,i)=>`${i+1}. ${p.name}`).join('\n'),url=d?.google_maps_url||'';
  const modal=document.createElement('div');modal.className='jarvis-modal';
  modal.innerHTML=`<div class="jarvis-modal-card"><button class="jarvis-close" type="button" data-action="close-modal">×</button><h2>🗺 ${esc(t('route_ready'))}</h2><p class="jarvis-route-text">${esc(names)}</p>${d?.total_distance_km!=null?`<p>${esc(t('distance'))}: ${esc(String(d.total_distance_km))} км</p>`:''}<p class="jarvis-route-url">${esc(url)}</p><button class="btn-main" type="button" data-action="open-route" data-url="${esc(url)}">${esc(t('open_maps'))}</button><button class="btn-route" type="button" data-action="copy-route" data-url="${esc(url)}">${esc(t('copy'))}</button></div>`;
  modal.addEventListener('click',e=>{if(e.target===modal)modal.remove()});document.body.appendChild(modal);
 }catch(e){toast(`Не удалось построить маршрут: ${e.message}`)}finally{if(btn)btn.disabled=state.route.length<2}
}
export function back(){go(state.route.length?'cards':'tags');}
export async function copyRoute(url){try{await navigator.clipboard.writeText(url);toast('Ссылка скопирована')}catch{toast('Не удалось скопировать ссылку')}}
export function openRoute(url){
 if(!url)return;
 try{
   if(tg?.openLink){tg.openLink(url,{try_instant_view:false});return;}
   window.open(url,'_blank','noopener,noreferrer');
 }catch{window.open(url,'_blank','noopener,noreferrer')}
}
