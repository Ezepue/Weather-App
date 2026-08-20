/* Service worker.

   Shell assets are cached ahead of time; API responses use stale-while-
   revalidate so a cold tunnel or a dead network still renders the last known
   weather instead of a browser error page. */

const VERSION = "barograph-v2";
const SHELL = `${VERSION}-shell`;
const DATA = `${VERSION}-data`;

const SHELL_ASSETS = [
  "/",
  "/static/css/tokens.css",
  "/static/css/base.css",
  "/static/css/components.css",
  "/static/js/main.js",
  "/static/img/favicon.svg",
  "/manifest.webmanifest",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(SHELL)
      .then((cache) => cache.addAll(SHELL_ASSETS))
      .catch(() => undefined)
      .then(() => self.skipWaiting()),
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(
        keys.filter((key) => !key.startsWith(VERSION)).map((key) => caches.delete(key)),
      ))
      .then(() => self.clients.claim()),
  );
});

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET") return;

  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;

  if (url.pathname.startsWith("/api/")) {
    event.respondWith(staleWhileRevalidate(request, DATA));
    return;
  }
  if (url.pathname.startsWith("/static/") || url.pathname === "/manifest.webmanifest") {
    event.respondWith(cacheFirst(request, SHELL));
    return;
  }
  event.respondWith(networkFirst(request, SHELL));
});

async function cacheFirst(request, cacheName) {
  const cached = await caches.match(request);
  if (cached) return cached;
  const response = await fetch(request);
  if (response.ok) (await caches.open(cacheName)).put(request, response.clone());
  return response;
}

async function staleWhileRevalidate(request, cacheName) {
  const cache = await caches.open(cacheName);
  const cached = await cache.match(request);
  const network = fetch(request)
    .then((response) => {
      if (response.ok) cache.put(request, response.clone());
      return response;
    })
    .catch(() => cached);
  return cached || network;
}

async function networkFirst(request, cacheName) {
  try {
    const response = await fetch(request);
    if (response.ok) (await caches.open(cacheName)).put(request, response.clone());
    return response;
  } catch {
    return (await caches.match(request)) || (await caches.match("/")) || Response.error();
  }
}
