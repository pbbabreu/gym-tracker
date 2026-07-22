// v3: runtime re-caching added (see the fetch handler) — the bump itself
// matters as much as the code change: it forces every installed device to
// reinstall this SW and re-cache CURRENT files, replacing whatever stale
// copy has been frozen in the old cache since that device's last SW update.
const CACHE = 'gym-tracker-v3';
// Relative (not root-absolute) paths on purpose: this app is hosted at a
// GitHub Pages *project* site (pbbabreu.github.io/gym-tracker/), not the
// domain root. Root-absolute paths like '/index.html' resolve against the
// domain root and 404 there — caches.addAll() fails atomically if any one
// request fails, so the old '/'-prefixed list silently broke offline
// caching entirely. Relative paths resolve against this file's own
// location instead, so they work regardless of the site's subpath.
const ASSETS = ['./', './index.html', './manifest.json', './library.json'];

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
