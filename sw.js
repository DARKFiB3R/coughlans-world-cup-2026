// ── Coughlans WC2026 Service Worker ──────────────────────────────────────────
// Strategy:
//   index.html  → always network-first (users always get the latest version)
//   logos/      → cache-first (static assets, rarely change)
//   everything else → network only (live API calls)

const CACHE = 'wc2026-assets-v1';

self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', e => e.waitUntil(self.clients.claim()));

self.addEventListener('fetch', e => {
  const { request } = e;
  const url = new URL(request.url);

  // ── Navigation (the HTML page itself) → always fetch fresh ──
  if (request.mode === 'navigate') {
    e.respondWith(
      fetch(request, { cache: 'no-store' })
        .catch(() => caches.match(request)) // offline fallback
    );
    return;
  }

  // ── Logos & squad JSON → cache-first, update in background ──
  if (url.pathname.includes('/logos/') || url.pathname.endsWith('squads.json')) {
    e.respondWith(
      caches.open(CACHE).then(cache =>
        cache.match(request).then(cached => {
          const networkFetch = fetch(request).then(res => {
            cache.put(request, res.clone());
            return res;
          });
          return cached || networkFetch;
        })
      )
    );
    return;
  }

  // ── Everything else (ESPN API, football-data.org) → network only ──
  e.respondWith(fetch(request));
});
