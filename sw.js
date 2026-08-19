/* IAMBANDOBANDZ bounded autopoietic runtime: same-origin LKG recovery only. */
'use strict';

const CACHE_NAME = 'iambandobandz-lkg-v1';
const CORE = [
  '/',
  '/styles.css',
  '/script.js',
  '/autopoietic-runtime.js',
  '/site.webmanifest',
  '/favicon.svg',
  '/.well-known/iambandobandz.json',
  '/.well-known/autopoiesis.json',
  '/network/',
  '/store/',
  '/privacy/',
  '/terms/'
];

async function notifyClients(message) {
  const clients = await self.clients.matchAll({ type: 'window', includeUncontrolled: true });
  await Promise.all(clients.map((client) => client.postMessage(message)));
}

self.addEventListener('install', (event) => {
  event.waitUntil((async () => {
    const cache = await caches.open(CACHE_NAME);
    await cache.addAll(CORE);
    await self.skipWaiting();
  })());
});

self.addEventListener('activate', (event) => {
  event.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key)));
    await self.clients.claim();
  })());
});

async function networkFirst(request) {
  const cache = await caches.open(CACHE_NAME);
  try {
    const response = await fetch(request);
    if (response && response.ok) await cache.put(request, response.clone());
    return response;
  } catch (error) {
    const cached = await cache.match(request, { ignoreSearch: true }) || await cache.match('/');
    if (cached) {
      await notifyClients({ type: 'LKG_SERVED', url: request.url });
      return cached;
    }
    throw error;
  }
}

async function staleWhileRevalidate(request) {
  const cache = await caches.open(CACHE_NAME);
  const cached = await cache.match(request, { ignoreSearch: true });
  const network = fetch(request).then(async (response) => {
    if (response && response.ok) await cache.put(request, response.clone());
    return response;
  }).catch(() => null);

  if (cached) {
    network.catch(() => null);
    return cached;
  }
  const response = await network;
  if (response) return response;
  const fallback = await cache.match('/');
  if (fallback) {
    await notifyClients({ type: 'LKG_SERVED', url: request.url });
    return fallback;
  }
  return new Response('Signal unavailable', {
    status: 503,
    headers: { 'Content-Type': 'text/plain; charset=utf-8' }
  });
}

self.addEventListener('fetch', (event) => {
  const request = event.request;
  if (request.method !== 'GET') return;

  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;

  const wantsHtml =
    request.mode === 'navigate' ||
    request.destination === 'document' ||
    request.headers.get('accept')?.includes('text/html');

  event.respondWith(wantsHtml ? networkFirst(request) : staleWhileRevalidate(request));
});

self.addEventListener('message', (event) => {
  if (event.data?.type === 'SKIP_WAITING') self.skipWaiting();
});
