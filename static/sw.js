/**
 * Swasthya Setu — Progressive Web App Service Worker
 * Offline-first: caches static assets + patient dashboard
 * Sensitive data (records/vitals) uses network-first strategy
 */

const CACHE_VERSION = 'swasthya-v1.2';
const STATIC_CACHE = `${CACHE_VERSION}-static`;
const DYNAMIC_CACHE = `${CACHE_VERSION}-dynamic`;

// Assets to pre-cache on install
const PRECACHE_URLS = [
  '/dashboard/',
  '/static/js/app.js',
  '/static/js/translations.js',
  '/static/js/charts.js',
  '/static/js/voice_ai.js',
  '/static/js/emergency.js',
  '/static/js/hospital_maps_booking.js',
  '/static/css/style.css',
  // Offline fallback page
  '/offline/'
];

// API routes that should NEVER be cached (security-sensitive)
const NEVER_CACHE = [
  '/api/vitals/',
  '/api/records/',
  '/login/',
  '/logout/',
  '/api/aadhaar/',
  '/api/patient/sos/',
  '/api/patient/feedback/',
  '/admin-portal/',
  '/hospital-portal/',
  '/doctor-portal/',
];

// ==================== INSTALL ====================
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(STATIC_CACHE).then(cache => {
      return cache.addAll(PRECACHE_URLS).catch(err => {
        console.warn('[SW] Pre-cache partial failure (OK in dev):', err);
      });
    }).then(() => self.skipWaiting())
  );
});

// ==================== ACTIVATE ====================
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys => {
      return Promise.all(
        keys.filter(key => key !== STATIC_CACHE && key !== DYNAMIC_CACHE)
            .map(key => {
              console.log('[SW] Deleting old cache:', key);
              return caches.delete(key);
            })
      );
    }).then(() => self.clients.claim())
  );
});

// ==================== FETCH STRATEGY ====================
self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);
  const pathname = url.pathname;

  // Skip non-GET requests and cross-origin
  if (event.request.method !== 'GET' || url.origin !== location.origin) return;

  // Never cache sensitive API routes
  if (NEVER_CACHE.some(path => pathname.startsWith(path))) {
    event.respondWith(fetch(event.request).catch(() => new Response(
      JSON.stringify({ status: 'offline', message: 'No internet connection.' }),
      { headers: { 'Content-Type': 'application/json' } }
    )));
    return;
  }

  // Static assets: cache-first
  if (pathname.startsWith('/static/')) {
    event.respondWith(
      caches.match(event.request).then(cached => {
        if (cached) return cached;
        return fetch(event.request).then(response => {
          const clone = response.clone();
          caches.open(STATIC_CACHE).then(cache => cache.put(event.request, clone));
          return response;
        });
      })
    );
    return;
  }

  // Dashboard: network-first, fallback to cache then offline page
  if (pathname === '/dashboard/' || pathname === '/') {
    event.respondWith(
      fetch(event.request)
        .then(response => {
          const clone = response.clone();
          caches.open(DYNAMIC_CACHE).then(cache => cache.put(event.request, clone));
          return response;
        })
        .catch(() => caches.match(event.request)
          .then(cached => cached || caches.match('/offline/'))
        )
    );
    return;
  }

  // Default: stale-while-revalidate
  event.respondWith(
    caches.match(event.request).then(cached => {
      const fetchPromise = fetch(event.request).then(response => {
        caches.open(DYNAMIC_CACHE).then(cache => {
          if (response.ok) cache.put(event.request, response.clone());
        });
        return response;
      });
      return cached || fetchPromise;
    })
  );
});

// ==================== MESSAGE: LOGOUT CACHE CLEAR ====================
self.addEventListener('message', event => {
  if (event.data && event.data.type === 'LOGOUT_CLEAR_CACHE') {
    caches.keys().then(keys => {
      Promise.all(keys.map(key => caches.delete(key))).then(() => {
        console.log('[SW] All caches cleared on logout.');
        event.ports[0]?.postMessage({ status: 'cleared' });
      });
    });
  }
});
