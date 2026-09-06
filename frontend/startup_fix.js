(() => {
  const start = document.getElementById('start-travel');
  if (!start) return;

  let requested = false;

  function forceTravelScreen() {
    const regions = document.getElementById('regions');
    if (!regions) return false;

    requested = true;
    window.__jarvisStartRequested = true;

    document.querySelectorAll('.screen').forEach(screen => {
      screen.classList.remove('active');
      screen.style.display = '';
    });

    regions.classList.add('active');
    regions.style.display = 'block';

    const nav = document.getElementById('bottom-nav');
    if (nav) nav.style.display = 'flex';

    document.querySelectorAll('.bottom-nav-item').forEach(item => {
      item.classList.toggle('active', item.dataset.tab === 'travel');
    });

    try { window.Telegram?.WebApp?.HapticFeedback?.impactOccurred?.('light'); } catch (_) {}
    try { window.loadRegions?.(); } catch (_) {}
    return true;
  }

  const activate = event => {
    event.preventDefault();
    event.stopPropagation();
    forceTravelScreen();
  };

  // Pointer events are the lowest-level reliable path for mouse + touch in Telegram WebView.
  start.addEventListener('pointerdown', activate, { capture: true, passive: false });
  start.addEventListener('click', activate, { capture: true, passive: false });

  // Fallback for older WebViews without reliable PointerEvent support.
  start.addEventListener('touchend', activate, { capture: true, passive: false });

  // Protect against app.js restoring a stale saved screen while its async init finishes.
  const guard = setInterval(() => {
    if (!requested) return;
    const splash = document.getElementById('splash');
    const regions = document.getElementById('regions');
    if (regions && splash && splash.classList.contains('active')) forceTravelScreen();
  }, 50);

  setTimeout(() => clearInterval(guard), 5000);
})();
