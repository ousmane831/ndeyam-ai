/*
 * Service worker Ndeyam AI : rend l'application installable et garde l'interface en cache pour qu'elle
 * s'ouvre vite, même avec une connexion faible. Les données (/api) ne sont JAMAIS mises en cache ici :
 * elles restent celles du serveur (le mode hors ligne des données viendra avec une synchronisation dédiée).
 */
// Remplacé à chaque construction (identifiant de version) : une nouvelle version recharge toute l'interface.
const CACHE = 'ndeyam-interface-__BUILD_ID__'
const SHELL = ['/', '/manifest.webmanifest', '/favicon.svg', '/icons/icon-192.png', '/icons/icon-512.png']

// À l'installation : toute l'interface (liste produite à la construction), pour qu'elle s'ouvre hors ligne,
// y compris les écrans jamais visités (≈ 400 Ko compressés, une seule fois par version).
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE).then(async (cache) => {
      await cache.addAll(SHELL)
      try {
        const assets = await (await fetch('/asset-list.json', { cache: 'no-store' })).json()
        await cache.addAll(assets)
      } catch {
        /* liste absente (développement) : les fichiers seront gardés au fil de l'usage */
      }
    }).then(() => self.skipWaiting()),
  )
})

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim()),
  )
})

const isFont = (url) => url.hostname === 'fonts.googleapis.com' || url.hostname === 'fonts.gstatic.com'

self.addEventListener('fetch', (event) => {
  const { request } = event
  if (request.method !== 'GET') return
  const url = new URL(request.url)
  const sameOrigin = url.origin === self.location.origin
  if (!sameOrigin && !isFont(url)) return
  if (sameOrigin && /^\/(api|admin|media|static)\//.test(url.pathname)) return

  // Pages : le réseau d'abord (version à jour), l'interface en cache si la connexion manque.
  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request)
        .then((res) => { const copy = res.clone(); caches.open(CACHE).then((c) => c.put('/', copy)); return res })
        .catch(() => caches.match('/')),
    )
    return
  }
  // Fichiers versionnés (/assets/…-hash.js) et polices : le cache d'abord, ils ne changent jamais.
  if ((sameOrigin && url.pathname.startsWith('/assets/')) || isFont(url)) {
    event.respondWith(
      caches.match(request).then((hit) => hit || fetch(request).then((res) => {
        if (res.ok || res.type === 'opaque') { const copy = res.clone(); caches.open(CACHE).then((c) => c.put(request, copy)) }
        return res
      })),
    )
    return
  }
  event.respondWith(fetch(request).catch(() => caches.match(request)))
})
