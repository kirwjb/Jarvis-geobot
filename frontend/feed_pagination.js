(() => {
  const PAGE_SIZE = 8;
  let currentPage = 0;
  let hasNextPage = false;
  let loading = false;

  function renderPageControls() {
    let box = document.getElementById('poi-pagination');
    if (!box) return;
    if (!S.filtered.length && !hasNextPage) {
      box.innerHTML = '';
      return;
    }
    box.innerHTML = `
      <button class="poi-page-btn" type="button" ${currentPage <= 0 || loading ? 'disabled' : ''} onclick="loadPoiPage(${currentPage - 1})">←</button>
      <span class="poi-page-label">Страница ${currentPage + 1}</span>
      <button class="poi-page-btn" type="button" ${!hasNextPage || loading ? 'disabled' : ''} onclick="loadPoiPage(${currentPage + 1})">→</button>
    `;
  }

  function renderCurrentPage() {
    const feed = document.getElementById('feed');
    if (!feed) return;
    if (!S.filtered.length) {
      feed.innerHTML = '<div style="text-align:center;padding:50px;color:var(--muted)">Ничего не найдено</div>';
      renderPageControls();
      return;
    }
    feed.innerHTML = S.filtered.map(place => {
      const id = String(place.id);
      const favorite = S.favs.has(id);
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
              <button class="poi-act ${favorite ? 'active' : ''}" type="button" onclick="event.stopPropagation(); toggleFav('${escapeAttr(id)}')">${favorite ? '❤️' : '♡'} Favorite</button>
              <button class="poi-act ${inRoute ? 'active' : ''}" type="button" onclick="event.stopPropagation(); toggleRoute('${escapeAttr(id)}')">${inRoute ? '✓' : '＋'} Route</button>
            </div>
          </div>
        </div>
      `;
    }).join('');
    renderPageControls();
  }

  window.loadPoiPage = async function(targetPage) {
    if (targetPage < 0 || loading) return;
    if (targetPage > currentPage && !hasNextPage) return;

    loading = true;
    const feed = document.getElementById('feed');
    if (feed) feed.innerHTML = '<div style="padding:50px;text-align:center;color:var(--muted)">Загрузка мест…</div>';

    try {
      const data = await apiFetch('/pois/query', {
        method: 'POST',
        body: JSON.stringify({
          region: S.region,
          city: S.city,
          tags: [...S.tags],
          limit: PAGE_SIZE + 1,
          offset: targetPage * PAGE_SIZE
        })
      });

      const pois = Array.isArray(data?.pois) ? data.pois : [];
      hasNextPage = pois.length > PAGE_SIZE;
      S.filtered = pois.slice(0, PAGE_SIZE);
      currentPage = targetPage;
      renderCurrentPage();
      document.getElementById('cards')?.scrollTo?.({ top: 0, behavior: 'smooth' });
    } catch (error) {
      console.error('Failed to load POI page:', error);
      if (feed) feed.innerHTML = `<div style="text-align:center;padding:50px;color:var(--muted)">Не удалось загрузить места<br><small>${escapeHtml(error.message)}</small></div>`;
    } finally {
      loading = false;
      renderPageControls();
    }
  };

  window.loadCards = async function() {
    if (!S.region || !S.city) { toast('Сначала выберите регион и город'); return; }
    if (S.tags.size === 0) { toast('Выберите хотя бы одну категорию'); return; }
    const feed = document.getElementById('feed');
    if (feed) feed.innerHTML = '<div style="padding:50px;text-align:center;color:var(--muted)">Загрузка мест…</div>';
    go('cards');
    currentPage = 0;
    hasNextPage = false;
    await loadPoiPage(0);
    const title = document.getElementById('cards-title');
    if (title) title.textContent = S.city || 'Места';
  };

  window.renderFeed = renderCurrentPage;
})();
