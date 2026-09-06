(() => {
  const PAGE_SIZE = 8;
  const pageCache = new Map();
  let page = 0;
  let loadingPage = false;
  let hasNextPage = false;

  const cacheKey = () => JSON.stringify({region: S.region, city: S.city, tags: [...S.tags].sort()});

  function skeletons() {
    return Array.from({length: PAGE_SIZE}, () => `
      <div class="poi-card poi-skeleton" aria-hidden="true">
        <div class="poi-img skeleton-block"></div>
        <div class="poi-body"><div class="skeleton-line wide"></div><div class="skeleton-line"></div><div class="skeleton-line short"></div></div>
      </div>`).join('');
  }

  function renderCurrentPage() {
    const feed = document.getElementById('feed');
    if (!feed) return;
    const pois = pageCache.get(`${cacheKey()}:${page}`) || [];
    S.filtered = pois;
    if (!pois.length) feed.innerHTML = '<div style="text-align:center;padding:50px;color:var(--muted)">Ничего не найдено</div>';
    else feed.innerHTML = pois.map(place => {
      const id = String(place.id);
      const image = place.images?.medium || place.images?.thumb || place.image_url || place.photo?.local_url_medium;
      const fav = S.favs.has(id), route = S.route.some(x => String(x.id) === id);
      return `<div class="poi-card" role="button" tabindex="0" onclick="openPoiDetail('${escapeAttr(id)}')" onkeydown="if(event.key==='Enter'||event.key===' ')openPoiDetail('${escapeAttr(id)}')">
        <div class="poi-img">${image ? `<img src="${escapeAttr(image)}" alt="${escapeAttr(place.name)}" loading="lazy" onerror="this.parentElement.innerHTML='<div class=\'jarvis-detail-placeholder\'>🏛️</div>'">` : '<div class="jarvis-detail-placeholder">🏛️</div>'}</div>
        <div class="poi-body"><div class="poi-name">${escapeHtml(place.name)}</div><div class="poi-loc">📍 ${escapeHtml(place.city || '')}</div>${place.address ? `<div class="poi-loc">${escapeHtml(place.address)}</div>` : ''}<div class="poi-actions"><button class="poi-act ${fav?'active':''}" onclick="event.stopPropagation();toggleFav('${escapeAttr(id)}')">${fav?'❤️':'♡'} Favorite</button><button class="poi-act ${route?'active':''}" onclick="event.stopPropagation();toggleRoute('${escapeAttr(id)}')">${route?'✓':'＋'} Route</button></div></div></div>`;
    }).join('');
    renderPagination();
  }

  function renderPagination() {
    const box = document.getElementById('poi-pagination');
    if (!box) return;
    box.innerHTML = `<button class="poi-page-btn" ${page===0?'disabled':''} onclick="changePoiPage(${page-1})">←</button><span class="poi-page-label">${page+1}${hasNextPage?' / …':''}</span><button class="poi-page-btn" ${!hasNextPage?'disabled':''} onclick="changePoiPage(${page+1})">→</button>`;
  }

  window.changePoiPage = async nextPage => {
    if (nextPage < 0 || loadingPage) return;
    const key = `${cacheKey()}:${nextPage}`;
    if (pageCache.has(key)) { page = nextPage; hasNextPage = pageCache.get(`${cacheKey()}:${nextPage}:hasNext`) === true; renderCurrentPage(); document.getElementById('cards')?.scrollTo({top:0,behavior:'smooth'}); return; }
    loadingPage = true;
    document.getElementById('feed').innerHTML = skeletons();
    try {
      const data = await apiFetch('/pois/query', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({region:S.region,city:S.city,tags:[...S.tags],limit:PAGE_SIZE+1,offset:nextPage*PAGE_SIZE})});
      const pois = data?.places || data?.pois || [];
      pageCache.set(key, pois.slice(0,PAGE_SIZE));
      pageCache.set(`${cacheKey()}:${nextPage}:hasNext`, pois.length > PAGE_SIZE);
      page = nextPage; hasNextPage = pois.length > PAGE_SIZE; renderCurrentPage();
      document.getElementById('cards')?.scrollTo({top:0,behavior:'smooth'}); haptic('light');
    } catch (e) { document.getElementById('feed').innerHTML='<div style="text-align:center;padding:50px;color:var(--muted)">Не удалось загрузить места.<br>Попробуйте ещё раз.</div>'; toast(e.message || 'Ошибка загрузки'); }
    finally { loadingPage = false; }
  };

  window.loadCards = async () => {
    if (!S.region || !S.city) return toast('Сначала выберите регион и город');
    if (!S.tags.size) return toast('Выберите хотя бы одну категорию');
    go('cards'); page=0; loadingPage=true; pageCache.clear();
    document.getElementById('feed').innerHTML=skeletons(); renderPagination();
    try {
      const data=await apiFetch('/pois/query',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({region:S.region,city:S.city,tags:[...S.tags],limit:PAGE_SIZE+1,offset:0})});
      const pois=data?.places || data?.pois || [];
      const base=cacheKey(); pageCache.set(`${base}:0`,pois.slice(0,PAGE_SIZE)); pageCache.set(`${base}:0:hasNext`,pois.length>PAGE_SIZE); hasNextPage=pois.length>PAGE_SIZE; renderCurrentPage();
    } catch(e) { document.getElementById('feed').innerHTML='<div style="text-align:center;padding:50px;color:var(--muted)">Не удалось загрузить места.</div>'; toast(e.message || 'Ошибка загрузки'); }
    finally { loadingPage=false; }
  };
})();