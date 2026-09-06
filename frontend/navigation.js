(() => {
  const nav = document.getElementById('bottom-nav');
  if (!nav) return;
  nav.insertAdjacentHTML('beforeend', '<button class="bottom-nav-item" type="button" data-tab="favorites" onclick="openFavorites()"><span class="bottom-nav-icon">♡</span><span class="bottom-nav-label">Favorites</span></button><button class="bottom-nav-item" type="button" data-tab="groups" onclick="openGroups()"><span class="bottom-nav-icon">👥</span><span class="bottom-nav-label">Groups</span></button>');

  const favScreen = document.createElement('div');
  favScreen.className = 'screen'; favScreen.id = 'favorites';
  favScreen.innerHTML = '<div class="topbar"><h2>Favorites</h2></div><div id="favorites-list"></div>';
  document.body.insertBefore(favScreen, document.getElementById('route'));

  const groupScreen = document.createElement('div');
  groupScreen.className = 'screen'; groupScreen.id = 'groups';
  groupScreen.innerHTML = '<div class="topbar"><h2>Groups</h2></div><div style="text-align:center;padding:30px;color:var(--muted)"><div style="font-size:48px;margin-bottom:12px">👥</div><h3>Travel groups</h3><p>Групповые поездки управляются через Telegram-бота.</p><button class="btn-main" type="button" onclick="sendGroupsToBot()">Открыть группы в Telegram</button></div>';
  document.body.insertBefore(groupScreen, document.getElementById('route'));

  const style = document.createElement('style'); style.textContent = '#favorites-list{display:grid;gap:12px;padding-bottom:30px}.favorite-item{padding:16px;border:1px solid var(--border);border-radius:18px;background:var(--panel)}.favorite-item h3{margin:0 0 7px}.favorite-item p{margin:0;color:var(--muted)}'; document.head.appendChild(style);

  window.openFavorites = async () => {
    document.querySelectorAll('.bottom-nav-item').forEach(x=>x.classList.toggle('active',x.dataset.tab==='favorites'));
    go('favorites'); const box=document.getElementById('favorites-list'); box.innerHTML='<div class="jarvis-loading"><div class="jarvis-spinner"></div><div class="jarvis-loading-title">Загружаем избранное…</div></div>';
    try { const data=await apiFetch('/favorites/me'); const list=data?.favorites||[]; box.innerHTML=list.length?list.map(f=>`<div class="favorite-item"><h3>${escapeHtml(f.place_name)}</h3><p>${escapeHtml(f.address||'')}</p><button class="poi-act" type="button" onclick="openPoiDetail('${escapeAttr(String(f.place_id))}')">Открыть</button></div>`).join(''):'<div style="text-align:center;padding:50px;color:var(--muted)">Пока ничего нет в избранном ❤️</div>'; }
    catch(e){ box.innerHTML='<div style="text-align:center;padding:50px;color:var(--muted)">Избранное доступно при открытии через Telegram.</div>'; }
  };
  window.openGroups = () => { document.querySelectorAll('.bottom-nav-item').forEach(x=>x.classList.toggle('active',x.dataset.tab==='groups')); go('groups'); };
  window.sendGroupsToBot = () => { if(window.Telegram?.WebApp?.sendData){ try{window.Telegram.WebApp.sendData('groups');return;}catch(_){} } toast('Откройте JARVIS в Telegram, чтобы управлять группами'); };
})();