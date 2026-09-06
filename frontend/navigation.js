(() => {
  const nav = document.getElementById('bottom-nav');

  // The splash CTA gets its own real event listener as a fallback to the inline handler.
  // This also makes the button reliable inside Telegram WebView after cached assets update.
  const startButton = document.getElementById('start-travel');
  if (startButton) {
    startButton.addEventListener('click', event => {
      event.preventDefault();
      try {
        window.Telegram?.WebApp?.HapticFeedback?.impactOccurred?.('light');
      } catch (_) {}
      if (typeof window.go === 'function') {
        window.go('regions');
      } else {
        document.querySelectorAll('.screen').forEach(screen => screen.classList.remove('active'));
        document.getElementById('regions')?.classList.add('active');
      }
    });
  }

  if (!nav) return;

  nav.insertAdjacentHTML('beforeend', `
    <button class="bottom-nav-item" type="button" data-tab="favorites">
      <span class="bottom-nav-icon">♡</span><span class="bottom-nav-label" data-i18n="Favorites">Favorites</span>
    </button>
    <button class="bottom-nav-item" type="button" data-tab="groups">
      <span class="bottom-nav-icon">👥</span><span class="bottom-nav-label" data-i18n="Groups">Groups</span>
    </button>
  `);

  const favScreen = document.createElement('div');
  favScreen.className = 'screen'; favScreen.id = 'favorites';
  favScreen.innerHTML = '<div class="topbar"><h2 data-i18n="Favorites">Favorites</h2></div><div id="favorites-list"></div>';
  document.body.insertBefore(favScreen, document.getElementById('route'));

  const groupScreen = document.createElement('div');
  groupScreen.className = 'screen'; groupScreen.id = 'groups';
  groupScreen.innerHTML = '<div class="topbar"><h2 data-i18n="Groups">Groups</h2></div><div style="text-align:center;padding:30px;color:var(--muted)"><div style="font-size:48px;margin-bottom:12px">👥</div><h3 data-i18n="Travel groups">Travel groups</h3><p data-i18n="Travel groups managed through Telegram">Travel groups are managed through the Telegram bot.</p><button class="btn-main" id="groups-open-btn" type="button" data-i18n="Open groups in Telegram">Open groups in Telegram</button></div>';
  document.body.insertBefore(groupScreen, document.getElementById('route'));

  const style = document.createElement('style');
  style.textContent = '#favorites-list{display:grid;gap:12px;padding-bottom:30px}.favorite-item{padding:16px;border:1px solid var(--border);border-radius:18px;background:var(--panel)}.favorite-item h3{margin:0 0 7px}.favorite-item p{margin:0;color:var(--muted)}.bottom-nav-item{cursor:pointer;touch-action:manipulation}.splash-wrap,.splash-wrap *{pointer-events:auto}.splash-wrap .btn-main{position:relative;z-index:2;touch-action:manipulation}';
  document.head.appendChild(style);

  function activate(tab) {
    document.querySelectorAll('.bottom-nav-item').forEach(item => item.classList.toggle('active', item.dataset.tab === tab));
  }

  async function openFavorites() {
    activate('favorites');
    go('favorites');
    const box = document.getElementById('favorites-list');
    if (!box) return;
    box.innerHTML = '<div class="jarvis-loading"><div class="jarvis-spinner"></div><div class="jarvis-loading-title" data-i18n="Loading favorites">Loading favorites…</div></div>';
    try {
      const data = await apiFetch('/favorites/me');
      const list = data?.favorites || [];
      box.innerHTML = list.length
        ? list.map(f => `<div class="favorite-item"><h3>${escapeHtml(f.place_name || '')}</h3><p>${escapeHtml(f.address || '')}</p><button class="poi-act" type="button" onclick="openPoiDetail('${escapeAttr(String(f.place_id))}')" data-i18n="Open">Open</button></div>`).join('')
        : '<div style="text-align:center;padding:50px;color:var(--muted)" data-i18n="No favorites yet">No favorites yet ❤️</div>';
    } catch (e) {
      console.error('Favorites failed:', e);
      box.innerHTML = '<div style="text-align:center;padding:50px;color:var(--muted)" data-i18n="Favorites require Telegram">Favorites are available when the Mini App is opened through Telegram.</div>';
    }
    if (window.applyLanguage) window.applyLanguage(localStorage.getItem('jarvis-language-v2') || 'ru', false);
  }

  function openGroups() { activate('groups'); go('groups'); }
  function sendGroupsToBot() {
    if (window.Telegram?.WebApp?.sendData) {
      try { window.Telegram.WebApp.sendData('groups'); return; } catch (_) {}
    }
    toast('Откройте JARVIS в Telegram, чтобы управлять группами');
  }

  nav.querySelectorAll('.bottom-nav-item[data-tab="travel"], .bottom-nav-item[data-tab="weather"]').forEach(item => item.addEventListener('click', () => bottomNavigate(item.dataset.tab)));
  nav.querySelector('[data-tab="favorites"]')?.addEventListener('click', openFavorites);
  nav.querySelector('[data-tab="groups"]')?.addEventListener('click', openGroups);
  document.getElementById('groups-open-btn')?.addEventListener('click', sendGroupsToBot);

  window.openFavorites = openFavorites;
  window.openGroups = openGroups;
  window.sendGroupsToBot = sendGroupsToBot;
})();
