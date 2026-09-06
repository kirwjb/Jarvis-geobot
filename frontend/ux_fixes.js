(() => {
  const PAGE_SIZE = 8;
  const pageCache = new Map();
  let currentPage = 0;
  let hasNextPage = false;
  let loading = false;
  let queryKey = '';

  const loadingMarkup = (count = PAGE_SIZE) => `
    <div class="jarvis-loading" aria-live="polite">
      <div class="jarvis-spinner"></div>
      <div class="jarvis-loading-title">JARVIS ищет места…</div>
      <div class="jarvis-skeleton-feed">
        ${Array.from({length: Math.min(count, 8)}, () => `
          <div class="poi-skeleton">
            <div class="poi-skeleton-img"></div>
            <div class="poi-skeleton-body"><div class="poi-skeleton-line wide"></div><div class="poi-skeleton-line"></div><div class="poi-skeleton-line short"></div><div class="poi-skeleton-actions"><span></span><span></span></div></div>
          </div>`).join('')}
      </div>
    </div>`;

  function ensureStyles() {
    if (document.getElementById('jarvis-ux-fixes-style')) return;
    const style = document.createElement('style');
    style.id = 'jarvis-ux-fixes-style';
    style.textContent = `
      .jarvis-loading { padding: 18px 0 28px; text-align:center; }
      .jarvis-spinner { width:28px; height:28px; margin:4px auto 10px; border:3px solid var(--border); border-top-color:var(--blue); border-radius:50%; animation:jarvis-spin .8s linear infinite; }
      @keyframes jarvis-spin { to { transform:rotate(360deg); } }
      .jarvis-loading-title { color:var(--muted); font-size:13px; margin-bottom:14px; }
      .jarvis-skeleton-feed { display:grid; gap:12px; text-align:left; }
      .poi-skeleton { overflow:hidden; display:grid; grid-template-columns:38% 1fr; min-height:148px; border:1px solid var(--border); border-radius:18px; background:var(--panel); }
      .poi-skeleton-img, .poi-skeleton-line, .poi-skeleton-actions span { background:linear-gradient(90deg,var(--panel-2),var(--input),var(--panel-2)); background-size:200% 100%; animation:jarvis-shimmer 1.35s ease-in-out infinite; }
      .poi-skeleton-img { min-height:148px; }
      .poi-skeleton-body { padding:15px; }
      .poi-skeleton-line { height:11px; border-radius:8px; margin-bottom:10px; width:72%; }
      .poi-skeleton-line.wide { width:92%; height:16px; }
      .poi-skeleton-line.short { width:48%; }
      .poi-skeleton-actions { display:flex; gap:8px; margin-top:20px; }
      .poi-skeleton-actions span { display:block; height:32px; flex:1; border-radius:9px; }
      @keyframes jarvis-shimmer { 0% { background-position:200% 0; } 100% { background-position:-200% 0; } }
      .poi-page-btn.is-loading { opacity:.55; }
    `;
    document.head.appendChild(style);
  }

  function makeKey() {
    return JSON.stringify({ region:S.region, city:S.city, tags:[...S.tags].sort() });
  }

  function renderPage() {
    const feed = document.getElementById('feed');
    const box = document.getElementById('poi-pagination');
    if (!feed) return;
    const places = S.filtered || [];
    if (!places.length) {
      feed.innerHTML = '<div style="text-align:center;padding:50px;color:var(--muted)">Ничего не найдено</div>';
    } else {
      feed.innerHTML = places.map(place => {
        const id = String(place.id);
        const favorite = S.favs.has(id);
        const inRoute = S.route.some(item => String(item.id) === id);
        const image = place.images?.medium || place.images?.thumb || place.image_url;
        return `<div class="poi-card" role="button" tabindex="0" onclick="openPoiDetail('${escapeAttr(id)}')" onkeydown="if(event.key==='Enter'||event.key===' ')openPoiDetail('${escapeAttr(id)}')">
          <div class="poi-img">${image ? `<img src="${escapeAttr(image)}" alt="${escapeAttr(place.name)}" loading="lazy">` : '<div class="jarvis-detail-placeholder" style="height:100%">🏛️</div>'}</div>
          <div class="poi-body"><div class="poi-name">${escapeHtml(place.name)}</div><div class="poi-loc">📍 ${escapeHtml(place.city || '')}</div>${place.address ? `<div class="poi-loc">${escapeHtml(place.address)}</div>` : ''}<div class="poi-actions"><button class="poi-act ${favorite ? 'active' : ''}" type="button" onclick="event.stopPropagation(); toggleFav('${escapeAttr(id)}')">${favorite ? '❤️' : '♡'} Favorite</button><button class="poi-act ${inRoute ? 'active' : ''}" type="button" onclick="event.stopPropagation(); toggleRoute('${escapeAttr(id)}')">${inRoute ? '✓' : '＋'} Route</button></div></div>
        </div>`;
      }).join('');
    }
    if (box) box.innerHTML = places.length || hasNextPage ? `<button class="poi-page-btn" type="button" ${currentPage <= 0 || loading ? 'disabled' : ''} onclick="loadPoiPage(${currentPage - 1})">←</button><span class="poi-page-label">Страница ${currentPage + 1}</span><button class="poi-page-btn" type="button" ${!hasNextPage || loading ? 'disabled' : ''} onclick="loadPoiPage(${currentPage + 1})">→</button>` : '';
  }

  async function fetchPage(targetPage, key) {
    const data = await apiFetch('/pois/query', { method:'POST', body:JSON.stringify({region:S.region, city:S.city, tags:[...S.tags], limit:PAGE_SIZE + 1, offset:targetPage * PAGE_SIZE}) });
    const pois = Array.isArray(data?.pois) ? data.pois : [];
    const pageData = { places:pois.slice(0,PAGE_SIZE), hasNext:pois.length > PAGE_SIZE };
    if (key === queryKey) pageCache.set(targetPage, pageData);
    return pageData;
  }

  window.loadPoiPage = async function(targetPage) {
    if (targetPage < 0 || loading) return;
    const key = makeKey();
    if (key !== queryKey) { pageCache.clear(); queryKey = key; currentPage = 0; hasNextPage = false; }
    const cached = pageCache.get(targetPage);
    if (cached) {
      currentPage = targetPage;
      S.filtered = cached.places;
      hasNextPage = cached.hasNext;
      renderPage();
      document.getElementById('cards')?.scrollTo?.({top:0, behavior:'smooth'});
      haptic('light');
      return;
    }
    if (targetPage > currentPage && !hasNextPage) return;
    loading = true;
    renderPage();
    const feed = document.getElementById('feed');
    if (!S.filtered?.length) feed && (feed.innerHTML = loadingMarkup());
    try {
      const result = await fetchPage(targetPage, key);
      if (key !== queryKey) return;
      currentPage = targetPage;
      S.filtered = result.places;
      hasNextPage = result.hasNext;
      renderPage();
      document.getElementById('cards')?.scrollTo?.({top:0, behavior:'smooth'});
      haptic('light');
    } catch (error) {
      console.error('Failed to load POI page:', error);
      if (!S.filtered?.length && feed) feed.innerHTML = `<div style="text-align:center;padding:50px;color:var(--muted)">Не удалось загрузить места<br><small>${escapeHtml(error.message)}</small></div>`;
      else toast(`Не удалось загрузить страницу: ${error.message}`);
    } finally {
      loading = false;
      renderPage();
    }
  };

  window.loadCards = async function() {
    if (!S.region || !S.city) { toast('Сначала выберите регион и город'); return; }
    if (S.tags.size === 0) { toast('Выберите хотя бы одну категорию'); return; }
    go('cards');
    pageCache.clear(); queryKey = makeKey(); currentPage = 0; hasNextPage = false; S.filtered = [];
    ensureStyles();
    const feed = document.getElementById('feed');
    if (feed) feed.innerHTML = loadingMarkup();
    const title = document.getElementById('cards-title');
    if (title) title.textContent = S.city || 'Места';
    await window.loadPoiPage(0);
  };

  window.renderFeed = renderPage;

  window.copyRouteLink = async function(url) {
    const value = String(url || '');
    if (!value) { toast('Ссылка на маршрут отсутствует'); return; }
    try {
      await navigator.clipboard.writeText(value);
      toast('Ссылка скопирована');
      return;
    } catch (_) {}
    try {
      const area = document.createElement('textarea');
      area.value = value; area.setAttribute('readonly','');
      area.style.position='fixed'; area.style.opacity='0'; area.style.pointerEvents='none';
      document.body.appendChild(area); area.focus(); area.select(); area.setSelectionRange(0, area.value.length);
      const ok = document.execCommand('copy'); area.remove();
      if (ok) { toast('Ссылка скопирована'); return; }
    } catch (_) {}
    toast('Не удалось скопировать — ссылку можно выделить вручную');
  };

  window.openRouteLink = function(url) {
    const value = String(url || '');
    if (!value) { toast('Ссылка на маршрут отсутствует'); return; }
    // Telegram openLink deliberately opens the URL outside the Mini App,
    // which is the most reliable way to hand Google Maps a directions URL.
    if (window.Telegram?.WebApp?.openLink) {
      try { window.Telegram.WebApp.openLink(value, {try_instant_view:false}); return; } catch (_) {}
    }
    try { window.open(value, '_blank', 'noopener,noreferrer'); } catch (_) { location.href = value; }
  };

  ensureStyles();
})();