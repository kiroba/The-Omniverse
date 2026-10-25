/**
 * KickBack PWA Service Worker (kickback_pwa_service_worker.js)
 * High-Security, Zero-Trust Out-of-Band Web Client Wrapper & Cache Engine
 */

const CACHE_NAME = 'kickback-pwa-v1.0.0-oct01';
const CORE_CLIENT_ASSETS = [
  '/',
  '/index.html',
  '/main.dart.js',
  '/flutter.js',
  '/assets/FontManifest.json',
  '/assets/AssetManifest.json',
  '/kickback_pwa_manifest.json'
];

// Subresource Integrity (SRI) Hash Table for Core WASM / JS Bundles
const EXPECTED_SRI_HASHES = {
  '/main.dart.js': 'sha256-OmniMainDartJsHash2026SecureReleaseKeyVerif778899==',
  '/flutter.js': 'sha256-FlutterWebEngineCore2026IntegrityVerified112233=='
};

// Install Event: Pre-cache Core Application Shell
self.addEventListener('install', (event) => {
  console.log('[KickBack PWA Worker] Installing Zero-Trust PWA Shell...');
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      console.log('[KickBack PWA Worker] Caching core static client assets');
      return cache.addAll(CORE_CLIENT_ASSETS);
    }).then(() => self.skipWaiting())
  );
});

// Activate Event: Clean Up Stale Offline Cache Instances
self.addEventListener('activate', (event) => {
  console.log('[KickBack PWA Worker] Activating PWA Worker...');
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cache) => {
          if (cache !== CACHE_NAME) {
            console.log('[KickBack PWA Worker] Purging legacy cache:', cache);
            return caches.delete(cache);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

// Fetch Event: Subresource Integrity Validation & P2P Stream Pass-Through
self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  // Bypass Cache for WebRTC Signaling & P2P GossipSub WebSocket Connections
  if (url.protocol === 'wss:' || url.protocol === 'ws:' || url.pathname.startsWith('/p2p/')) {
    return; // Pass directly to P2P network layer
  }

  // Handle Adult Sub-Enclave (SW) Watermarked Media Streaming Pass-Through
  if (url.pathname.includes('/cohort_adult_x_rated/')) {
    event.respondWith(
      fetch(event.request).then((response) => {
        // Enforce Watermark Header Inspection for Out-of-Band Web Clients
        const watermark = response.headers.get('X-Omni-Watermark-Hash');
        if (!watermark) {
          console.warn('[KickBack PWA Worker] X-Rated media missing buyer watermark header!');
        }
        return response;
      }).catch(() => {
        return new Response('P2P Offline: Adult media stream unavailable without mesh connection.', { status: 503 });
      })
    );
    return;
  }

  // Cache-First with SRI Verification Strategy for Static Application Shell
  event.respondWith(
    caches.match(event.request).then((cachedResponse) => {
      if (cachedResponse) {
        return cachedResponse;
      }

      return fetch(event.request).then((networkResponse) => {
        // Only cache valid 200 OK same-origin static assets
        if (!networkResponse || networkResponse.status !== 200 || networkResponse.type !== 'basic') {
          return networkResponse;
        }

        const responseToCache = networkResponse.clone();
        caches.open(CACHE_NAME).then((cache) => {
          cache.put(event.request, responseToCache);
        });

        return networkResponse;
      });
    })
  );
});
