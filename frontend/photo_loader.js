(() => {
  const API = '/api';
  const loaded = new Set();
  const pending = new Set();

  async function loadPhoto(card) {
    const id = card?.dataset?.poiId;
    const img = card?.querySelector('.poi-img img');
    if (!id || !img || loaded.has(id) || pending.has(id)) return;

    pending.add(id);
    try {
      const initData = window.Telegram?.WebApp?.initData || '';
      const response = await fetch(`${API}/pois/${encodeURIComponent(id)}/photo`, {
        method: 'POST',
        headers: {
          Accept: 'application/json',
          ...(initData ? { Authorization: `tma ${initData}` } : {})
        }
      });
      if (!response.ok) return;
      const data = await response.json();
      const photo = data?.photo;
      const url = photo?.local_url_medium || photo?.local_url_thumb || photo?.original_url;
      if (!url) return;
      img.src = url;
      loaded.add(id);
    } catch (error) {
      console.warn('Photo warmup failed:', id, error);
    } finally {
      pending.delete(id);
    }
  }

  function scan() {
    document.querySelectorAll('.poi-card').forEach(card => {
      if (!card.dataset.poiId) {
        const action = card.querySelector('.poi-actions button');
        const match = action?.getAttribute('onclick')?.match(/toggleFav\('([^']+)'\)/);
        if (match) card.dataset.poiId = match[1];
      }
      loadPhoto(card);
    });
  }

  const observer = new MutationObserver(scan);
  observer.observe(document.body, { childList: true, subtree: true });
  window.addEventListener('load', scan);
  setTimeout(scan, 300);
})();
