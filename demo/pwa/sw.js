self.addEventListener('install', (event) => {
  self.skipWaiting();
});

self.addEventListener('fetch', (event) => {
  // Simple offline fallback
  event.respondWith(fetch(event.request).catch(() => caches.match(event.request)));
});
