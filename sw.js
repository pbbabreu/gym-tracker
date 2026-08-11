// v3: runtime re-caching added (see the fetch handler) — the bump itself
// matters as much as the code change: it forces every installed device to
// reinstall this SW and re-cache CURRENT files, replacing whatever stale
// copy has been frozen in the old cache since that device's last SW update.
// v4: vendor/supabase.js joined ASSETS — it must be in the install-time
// cache or the first OFFLINE load after an online one would boot the app
// without window.supabase (login/account sync silently absent).
// v5: notificationclick handler added (rest-timer alerts, 2026-08-11) — the
// bump forces every installed device to pick up this file's new listener;
// without it, a device whose SW was already active would keep running the
// old script (SW updates are lazy — a new sw.js is only fetched/installed
// on its own schedule) and the tap-a-notification-to-return behavior below
// would silently never reach existing installs.
const CACHE = 'gym-tracker-v5';
// Relative (not root-absolute) paths on purpose: this app is hosted at a
// GitHub Pages *project* site (pbbabreu.github.io/gym-tracker/), not the
// domain root. Root-absolute paths like '/index.html' resolve against the
// domain root and 404 there — caches.addAll() fails atomically if any one
// request fails, so the old '/'-prefixed list silently broke offline
// caching entirely. Relative paths resolve against this file's own
// location instead, so they work regardless of the site's subpath.
const ASSETS = ['./', './index.html', './manifest.json', './library.json', './vendor/supabase.js'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(ASSETS)));
  self.skipWaiting();
});
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(keys =>
    Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
  ));
  self.clients.claim();
});
// Network-first, cache as fallback — AND the cache is refreshed on every
// successful same-origin GET as it flows through. Without that re-cache
// step, the cache was written exactly once (at install) and only refreshed
// when sw.js itself changed bytes, so the offline fallback could serve an
// app version many deploys older than the live site — old code which then
// persist()s data shapes it doesn't know it's dropping (that's how
// tombstones would silently vanish offline). Same-origin only, deliberately:
// api.github.com (Gist sync) must never be served from cache — a fake
// "successful" offline pull would feed stale data into the merge and show
// a sync status that never actually happened.
self.addEventListener('fetch', e => {
  e.respondWith(
    fetch(e.request).then(resp => {
      if (e.request.method === 'GET' && resp.ok && new URL(e.request.url).origin === self.location.origin) {
        const copy = resp.clone(); // body streams are one-shot — clone before the page consumes it
        caches.open(CACHE).then(c => c.put(e.request, copy));
      }
      return resp;
    }).catch(() => caches.match(e.request))
  );
});

// Rest-timer notifications (index.html's signalRestDone(), 2026-08-11) are
// shown via this registration so they can surface while the tab isn't
// focused — tapping one should return to the app, the standard PWA
// pattern: focus an already-open tab if one exists, otherwise open one.
self.addEventListener('notificationclick', e => {
  e.notification.close();
  e.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then(list => {
      for (const c of list) { if ('focus' in c) return c.focus(); }
      if (self.clients.openWindow) return self.clients.openWindow('./');
    })
  );
});
