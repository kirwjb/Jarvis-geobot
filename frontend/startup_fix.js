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

  window.__jarvisForceTravel = forceTravelScreen;

  function activate(event) {
    event.preventDefault();
    event.stopPropagation();
    forceTravelScreen();
  }

  start.addEventListener('pointerup', activate, { capture: true, passive: false });
  start.addEventListener('click', activate, { capture: true, passive: false });
  start.addEventListener('touchend', activate, { capture: true, passive: false });

  /* Last-resort coordinate delegation. If Telegram/Chromium resolves the
     pointer target to a text node or another overlay, inspect every element
     under the pointer and trigger the actual control. */
  document.addEventListener('pointerup', event => {
    if (event.target === start || start.contains(event.target)) return;
    const stack = document.elementsFromPoint(event.clientX, event.clientY);
    if (stack.includes(start)) activate(event);
  }, { capture: true, passive: false });

  document.addEventListener('click', event => {
    if (event.target === start || start.contains(event.target)) return;
    const stack = document.elementsFromPoint(event.clientX, event.clientY);
    if (stack.includes(start)) activate(event);
  }, { capture: true, passive: false });

  const guard = setInterval(() => {
    if (!requested) return;
    const splash = document.getElementById('splash');
    const regions = document.getElementById('regions');
    if (regions && splash && splash.classList.contains('active')) forceTravelScreen();
  }, 50);

  setTimeout(() => clearInterval(guard), 5000);
})();
