(() => {
  const PAGE_SIZE = 8;
  let page = 0;
  let loadingPage = false;

  function injectStyles() {
    if (document.getElementById('jarvis-enhancements-style')) return;
    const style = document.createElement('style');
    style.id = 'jarvis-enhancements-style';
    style.textContent = `
      .poi-card { cursor: pointer; }
      .poi-card:active { transform: scale(.995); }
      .poi-img img { width:100%; height:100%; object-fit:cover; display:block; }
      .poi-pagination { display:flex; align-items:center; justify-content:center; gap:8px; margin:4px 0 28px; }
      .poi-page-btn { min-width:42px; height:40px; padding:0 12px; border:1px solid var(--border); border-radius:11px; background:var(--panel); color:var(--text); font-weight:600; cursor:pointer; }
      .poi-page-btn:disabled { opacity:.35; cursor:not-allowed; }
      .poi-page-label { min-width:82px; text-align:center; color:var(--muted); font-size:13px; }
      .jarvis-modal { position:fixed; inset:0; z-index:9000; display:none; align-items:flex-end; justify-content:center; background:rgba(0,0,0,.58); backdrop-filter:blur(8px); -webkit-backdrop-filter:blur(8px); }
      .jarvis-modal.show { display:flex; }
      .jarvis-sheet { width:min(720px,100%); max-height:92vh; overflow:auto; border:1px solid var(--border); border-bottom:0; border-radius:24px 24px 0 0; background:var(--panel); color:var(--text); box-shadow:0 -12px 45px rgba(0,0,0,.28); animation:jarvis-sheet-in .22s ease; }
      @keyframes jarvis-sheet-in { from { transform:translateY(30px); opacity:.6; } to { transform:translateY(0); opacity:1; } }
      .jarvis-detail-img { width:100%; height:min(48vh,360px); background:var(--panel-2); object-fit:cover; display:block; }
      .jarvis-detail-placeholder { width:100%; height:190px; display:flex; align-items:center; justify-content:center; color:var(--muted); background:var(--panel-2); font-size:42px; }
      .jarvis-detail-body { padding:20px 18px calc(24px + env(safe-area-inset-bottom)); }
      .jarvis-detail-title { margin-bottom:9px; font-size:23px; line-height:1.2; font-weight:750; }
      .jarvis-detail-meta { display:flex; flex-wrap:wrap; gap:7px; margin-bottom:14px; }
      .jarvis-chip { padding:6px 9px; border-radius:9px; background:var(--panel-2); color:var(--muted); font-size:12px; }
      .jarvis-detail-row { margin:9px 0; color:var(--text-soft); font-size:14px; line-height:1.45; }
      .jarvis-detail-row strong { color:var(--text); }
      .jarvis-detail-actions { display:grid; grid-template-columns:1fr 1fr; gap:9px; margin-top:18px; }
      .jarvis-modal-btn { min-height:46px; border:1px solid var(--border); border-radius:13px; background:var(--input); color:var(--text); font-weight:650; cursor:pointer; }
      .jarvis-modal-btn.primary { border-color:transparent; background:linear-gradient(135deg,var(--blue),var(--blue-2)); color:#fff; }
      .jarvis-modal-btn.green { border-color:transparent; background:linear-gradient(135deg,var(--green),var(--green-2)); color:#fff; }
      .jarvis-close { position:absolute; top:12px; right:12px; width:38px; height:38px; border:1px solid rgba(255,255,255,.16); border-radius:50%; background:rgba(0,0,0,.38); color:#fff; font-size:20px; cursor:pointer; z-index:2; }
      .jarvis-route-text { white-space:pre-line; padding:14px; border:1px solid var(--border); border-radius:13px; background:var(--input); color:var(--text-soft); font-size:14px; line-height:1.5; user-select:text; word-break:break-word; }
      .jarvis-route-url { display:block; margin-top:10px; padding:12px; border:1px solid var(--border); border-radius:11px; background:var(--input); color:var(--blue); font-size:12px; line-height:1.4; user-select:text; word-break:break-all; }
      .jarvis-route-actions { display:grid; grid-template-columns:1fr 1fr; gap:9px; margin-top:12px; }
      @media (min-width:700px) { .jarvis-modal { align-items:center; padding:24px; } .jarvis-sheet { border-bottom:1px solid var(--border); border-radius:24px; max-height:88vh; } }
    `;
    document.head.appendChild(style);
  }

  function ensureModal() {
    let modal = document.getElementById('jarvis-modal');
    if (modal) return modal;
    modal = document.createElement('div');
    modal.id = 'jarvis-modal';
    modal.className = 'jarvis-modal';
    modal.addEventListener('click', event => {
      if (event.target === modal) closeJarvisModal();
    });
    document.body.appendChild(modal);
    return modal;
  }

  window.closeJarvisModal = function() {
    const modal = document.getElementById('jarvis-modal');
    if (modal) modal.classList.remove('show');
  };

  function openModal(html) {
    const modal = ensureModal();
    modal.innerHTML = `<div class="jarvis-sheet">${html}</div>`;
    modal.classList.add('show');
  }

  window.openPoiDetail = async function(id) {
    haptic('light');
    openModal('<div class="jarvis-detail-body"><div style="text-align:center;padding:45px;color:var(--muted)">Загрузка места…</div></div>');
    try {
      const place = await apiFetch(`/pois/${encodeURIComponent(id)}`);
      const image = place.images?.medium || place.images?.thumb || place.image_url || place.photo?.local_url_medium;
      const favorite = S.favs.has(String(place.id));
      const inRoute = S.route.some(item => String(item.id) === String(place.id));
      const details = [];
      if (place.address) details.push(`<div class="jarvis-detail-row">📍 <strong>Адрес:</strong> ${escapeHtml(place.address)}</div>`);
      if (place.hours) details.push(`<div class="jarvis-detail-row">🕒 <strong>Часы:</strong> ${escapeHtml(place.hours)}</div>`);
      if (place.phone) details.push(`<div class="jarvis-detail-row">☎️ <strong>Телефон:</strong> ${escapeHtml(place.phone)}</div>`);
      if (place.photo?.author) details.push(`<div class="jarvis-detail-row">📷 <strong>Автор:</strong> ${escapeHtml(place.photo.author)}</div>`);
      openModal(`
        <div style="position:relative">
          ${image ? `<img class="jarvis-detail-img" src="${escapeAttr(image)}" alt="${escapeAttr(place.name)}">` : '<div class="jarvis-detail-placeholder">🏛️</div>'}
          <button class="jarvis-close" type="button" onclick="closeJarvisModal()">×</button>
        </div>
        <div class="jarvis-detail-body">
          <div class="jarvis-detail-title">${escapeHtml(place.name)}</div>
          <div class="jarvis-detail-meta">
            ${place.category ? `<span class="jarvis-chip">${escapeHtml(place.category)}</span>` : ''}
            ${place.city ? `<span class="jarvis-chip">${escapeHtml(place.city)}</span>` : ''}
          </div>
          ${details.join('') || '<div class="jarvis-detail-row">Подробной информации пока нет.</div>'}
          <div class="jarvis-detail-actions">
            <button class="jarvis-modal-btn ${favorite ? 'primary' : ''}" type="button" onclick="toggleFav('${escapeAttr(String(place.id))}'); closeJarvisModal();">${favorite ? '❤️ В избранном' : '♡ В избранное'}</button>
            <button class="jarvis-modal-btn ${inRoute ? 'green' : ''}" type="button" onclick="toggleRoute('${escapeAttr(String(place.id))}'); closeJarvisModal();">${inRoute ? '✓ В маршруте' : '＋ В маршрут'}</button>
          </div>
        </div>
      `);
    } catch (error) {
      openModal(`<div class="jarvis-detail-body"><button class="jarvis-close" type="button" onclick="closeJarvisModal()">×</button><div style="padding:35px 0;text-align:center;color:var(--muted)">Не удалось загрузить место<br><small>${escapeHtml(error.message)}</small></div></div>`);
    }
  };

  window.copyRouteLink = async function(url) {
    try {
      await navigator.clipboard.writeText(url);
      toast('Ссылка скопирована');
    } catch (_) {
      toast('Не удалось скопировать — выделите ссылку вручную');
    }
  };

  window.openRouteLink = function(url) {
    if (tg?.openLink) {
      try {
        tg.openLink(url);
        return;
      } catch (_) {}
    }
    window.open(url, '_blank', 'noopener,noreferrer');
  };

  function showRouteModal(data) {
    const routeNames = S.route.map((place, index) => `${index + 1}. ${place.name}`).join('\n');
    const distance = data.total_distance_km != null ? `\n\nРасстояние: ${data.total_distance_km} км` : '';
    const url = data.google_maps_url || '';
    openModal(`
      <div class="jarvis-detail-body">
        <button class="jarvis-close" type="button" onclick="closeJarvisModal()">×</button>
        <div class="jarvis-detail-title">🗺 Маршрут готов</div>
        <div class="jarvis-route-text">${escapeHtml(routeNames)}${escapeHtml(distance)}</div>
        <div class="jarvis-route-url">${escapeHtml(url)}</div>
        <div class="jarvis-route-actions">
          <button class="jarvis-modal-btn primary" type="button" onclick="openRouteLink(${JSON.stringify(url)})">Открыть Google Maps</button>
          <button class="jarvis-modal-btn" type="button" onclick="copyRouteLink(${JSON.stringify(url)})">Копировать ссылку</button>
        </div>
      </div>
    `);
  }

  window.renderFeed = function() {
    const feed = document.getElementById('feed');
    if (!feed) return;

    if (!S.filtered.length) {
      feed.innerHTML = '<div style="text-align:center;padding:50px;color:var(--muted)">Ничего не найдено</div>';
      renderPagination();
      return;
    }

    const start = page * PAGE_SIZE;
    const visible = S.filtered.slice(start, start + PAGE_SIZE);
    feed.innerHTML = visible.map(place => {
      const id = String(place.id);
      const isFavorite = S.favs.has(id);
      const inRoute = S.route.some(item => String(item.id) === id);
      const image = place.images?.medium || place.images?.thumb || place.image_url;
      return `
        <div class="poi-card" role="button" tabindex="0" onclick="openPoiDetail('${escapeAttr(id)}')" onkeydown="if(event.key==='Enter'||event.key===' ')openPoiDetail('${escapeAttr(id)}')">
          <div class="poi-img">
            ${image ? `<img src="${escapeAttr(image)}" alt="${escapeAttr(place.name)}" loading="lazy">` : '<div class="jarvis-detail-placeholder" style="height:100%">🏛️</div>'}
          </div>
          <div class="poi-body">
            <div class="poi-name">${escapeHtml(place.name)}</div>
            <div class="poi-loc">📍 ${escapeHtml(place.city || '')}</div>
            ${place.address ? `<div class="poi-loc">${escapeHtml(place.address)}</div>` : ''}
            <div class="poi-actions">
              <button class="poi-act ${isFavorite ? 'active' : ''}" type="button" onclick="event.stopPropagation(); toggleFav('${escapeAttr(id)}')">${isFavorite ? '❤️' : '♡'} Favorite</button>
              <button class="poi-act ${inRoute ? 'active' : ''}" type="button" onclick="event.stopPropagation(); toggleRoute('${escapeAttr(id)}')">${inRoute ? '✓' : '＋'} Route</button>
            </div>
          </div>
        </div>
      `;
    }).join('');
    renderPagination();
  };

  function renderPagination() {
    let box = document.getElementById('poi-pagination');
    if (!box) {
      box = document.createElement('div');
      box.id = 'poi-pagination';
      box.className = 'poi-pagination';
      const feed = document.getElementById('feed');
      if (feed?.parentNode) feed.parentNode.insertBefore(box, feed.nextSibling);
    }
    const totalPages = Math.max(1, Math.ceil(S.filtered.length / PAGE_SIZE));
    if (totalPages <= 1) {
      box.innerHTML = '';
      return;
    }
    box.innerHTML = `
      <button class="poi-page-btn" type="button" ${page <= 0 ? 'disabled' : ''} onclick="changePoiPage(${page - 1})">←</button>
      <span class="poi-page-label">${page + 1} / ${totalPages}</span>
      <button class="poi-page-btn" type="button" ${page >= totalPages - 1 ? 'disabled' : ''} onclick="changePoiPage(${page + 1})">→</button>
    `;
  }

  window.changePoiPage = async function(nextPage) {
    const totalPages = Math.max(1, Math.ceil(S.filtered.length / PAGE_SIZE));
    if (nextPage < 0 || nextPage >= totalPages || loadingPage) return;
    page = nextPage;
    renderFeed();
    document.getElementById('cards')?.scrollTo?.({ top: 0, behavior: 'smooth' });
    haptic('light');
  };

  const originalLoadCards = window.loadCards;
  window.loadCards = async function() {
    if (!S.region || !S.city) { toast('Сначала выберите регион и город'); return; }
    if (S.tags.size === 0) { toast('Выберите хотя бы одну категорию'); return; }

    const feed = document.getElementById('feed');
    if (feed) feed.innerHTML = '<div style="padding:50px;text-align:center;color:var(--muted)">Загрузка мест…</div>';
    go('cards');
    page = 0;
    loadingPage = true;

    try {
      const data = await apiFetch('/pois/query', {
        method: 'POST',
        body: JSON.stringify({ region: S.region, city: S.city, tags: [...S.tags], limit: 30, offset: 0 })
      });
      S.filtered = Array.isArray(data?.pois) ? data.pois : [];
      const title = document.getElementById('cards-title');
      if (title) title.textContent = S.city || 'Места';
      renderFeed();
    } catch (error) {
      console.error('Failed to load POIs:', error);
      S.filtered = [];
      if (feed) feed.innerHTML = `<div style="text-align:center;padding:50px;color:var(--muted)">Не удалось загрузить места<br><small>${escapeHtml(error.message)}</small></div>`;
      toast(`Места недоступны: ${error.message}`);
    } finally {
      loadingPage = false;
    }
  };

  const originalBuildRoute = window.buildRoute;
  window.buildRoute = async function() {
    if (S.route.length < 2) { toast('Добавьте минимум 2 точки'); return; }
    const button = document.getElementById('btn-build');
    if (button) button.disabled = true;
    try {
      const data = await apiFetch('/route/build', {
        method: 'POST',
        body: JSON.stringify({ poi_ids: S.route.map(place => String(place.id)), optimize: true })
      });
      const byId = new Map(S.route.map(place => [String(place.id), place]));
      S.route = (data.poi_ids || []).map(id => byId.get(String(id))).filter(Boolean);
      renderRoute();
      saveState();
      showRouteModal(data);
      if (tg?.HapticFeedback?.notificationOccurred) tg.HapticFeedback.notificationOccurred('success');
    } catch (error) {
      console.error('Route build error:', error);
      toast(`Не удалось построить маршрут: ${error.message}`);
    } finally {
      if (button) button.disabled = S.route.length < 2;
    }
  };

  injectStyles();
  ensureModal();
})();
