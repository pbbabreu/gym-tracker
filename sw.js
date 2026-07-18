const CACHE = 'gym-tracker-v2';
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
self.addEventListener('fetch', e => {
  e.respondWith(
    fetch(e.request).catch(() => caches.match(e.request))
  );
});
