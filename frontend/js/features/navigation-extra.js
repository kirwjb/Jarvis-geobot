import { state, telegramUserId } from '../core/state.js';
import { request } from '../core/api.js';
import { $, esc, toast } from '../ui/helpers.js';
import { go, setTab } from '../core/router.js';
import { poiCardMarkup } from './places.js';
import { t } from '../ui/language.js';

export function installExtraNavigation(){
  const nav=$('#bottom-nav'); if(!nav||nav.dataset.extraInstalled)return;
  nav.dataset.extraInstalled='1';
  nav.insertAdjacentHTML('beforeend',`<button class="bottom-nav-item" type="button" data-tab="favorites"><span>♡</span><span data-i18n="favorites">${esc(t('favorites'))}</span></button><button class="bottom-nav-item" type="button" data-tab="groups"><span>👥</span><span data-i18n="groups">${esc(t('groups'))}</span></button>`);
  document.body.insertAdjacentHTML('beforeend',`<section class="screen" id="favorites"><div class="topbar"><h2 data-i18n="favorites">${esc(t('favorites'))}</h2></div><div class="feed" id="favorites-list"></div></section><section class="screen" id="groups"><div class="topbar"><h2 data-i18n="groups">${esc(t('groups'))}</h2></div><div class="empty" data-i18n="groups_hint">${esc(t('groups_hint'))}</div></section>`);
  nav.addEventListener('click',async e=>{const item=e.target.closest('[data-tab="favorites"],[data-tab="groups"]');if(!item)return;const tab=item.dataset.tab;setTab(tab);go(tab);if(tab==='favorites')await renderFavorites();});
  window.addEventListener('jarvis:favorites-changed',()=>{if(state.screen==='favorites')renderFavorites();});
  window.addEventListener('jarvis:language',()=>{if(state.screen==='favorites')renderFavorites();});
}

async function renderFavorites(){
  const box=$('#favorites-list');if(!box)return;
  if(!telegramUserId()){box.innerHTML=`<div class="empty">${esc(t('tg_only'))}</div>`;return;}
  box.innerHTML=`<div class="jarvis-loading"><div class="jarvis-spinner"></div><div class="jarvis-loading-title">${esc(t('loading'))}</div></div>`;
  try{
    const d=await request('/favorites/me'),list=d?.favorites||[];
    if(!list.length){box.innerHTML=`<div class="empty">${esc(t('fav_empty'))}</div>`;return;}
    const details=await Promise.all(list.map(async f=>{try{return await request(`/pois/${encodeURIComponent(f.place_id)}`)}catch(_){return {...f,id:f.place_id,name:f.place_name,city:'',address:f.address,images:null,image_url:null}}}));
    state.pois=details.filter(Boolean);
    box.innerHTML=state.pois.map(poiCardMarkup).join('');
  }catch(e){box.innerHTML=`<div class="empty">${esc(e.message||t('places_failed'))}</div>`;toast(e.message||t('places_failed'));}
}
