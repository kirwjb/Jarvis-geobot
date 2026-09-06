import { state, telegramUserId } from '../core/state.js';
import { request } from '../core/api.js';
import { $, esc, toast } from '../ui/helpers.js';
import { go, setTab } from '../core/router.js';

export function installExtraNavigation(){
  const nav=$('#bottom-nav'); if(!nav||nav.dataset.extraInstalled)return;
  nav.dataset.extraInstalled='1';
  nav.insertAdjacentHTML('beforeend','<button class="bottom-nav-item" type="button" data-tab="favorites"><span>♡</span><span>Избранное</span></button><button class="bottom-nav-item" type="button" data-tab="groups"><span>👥</span><span>Группы</span></button>');
  document.body.insertAdjacentHTML('beforeend','<section class="screen" id="favorites"><div class="topbar"><h2>Избранное</h2></div><div id="favorites-list"></div></section><section class="screen" id="groups"><div class="topbar"><h2>Группы</h2></div><div class="empty">Группы управляются через Telegram.</div></section>');
  nav.addEventListener('click',async e=>{const item=e.target.closest('[data-tab="favorites"],[data-tab="groups"]');if(!item)return;const tab=item.dataset.tab;setTab(tab);go(tab);if(tab==='favorites')await renderFavorites();});
}
async function renderFavorites(){const box=$('#favorites-list');if(!box)return;if(!telegramUserId()){box.innerHTML='<div class="empty">Откройте приложение через Telegram.</div>';return}box.innerHTML='<div class="loading">Загрузка избранного…</div>';try{const d=await request('/favorites/me');const list=d?.favorites||[];box.innerHTML=list.length?list.map(f=>`<article class="favorite-item"><h3>${esc(f.place_name||'Место')}</h3><p>${esc(f.address||'')}</p></article>`).join(''):'<div class="empty">Избранное пока пусто ❤️</div>'}catch(e){toast(e.message||'Не удалось загрузить избранное')}}
