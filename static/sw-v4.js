/* GroupPay Service Worker */
const CACHE_NAME = "grouppay-v1";
const OFFLINE_URLS = ["/", "/static/manifest.webmanifest"];

self.addEventListener("install", (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => cache.addAll(OFFLINE_URLS)).catch(() => {})
    );
    self.skipWaiting();
});

self.addEventListener("activate", (event) => {
    event.waitUntil(
        caches.keys().then((keys) =>
            Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
        )
    );
    self.clients.claim();
});

self.addEventListener("fetch", (event) => {
    const req = event.request;
    if (req.method !== "GET") return;
    if (req.headers.get("HX-Request")) return;

    event.respondWith(
        fetch(req)
            .then((res) => {
                if (res.ok && req.url.startsWith(self.location.origin)) {
                    const clone = res.clone();
                    caches.open(CACHE_NAME).then((c) => c.put(req, clone)).catch(() => {});
                }
                return res;
            })
            .catch(() => caches.match(req).then((r) => r || new Response("Offline", { status: 503 })))
    );
});


// ═══════════════════════════════════════════════════════════════
// PUSH NOTIFICATIONS
// ═══════════════════════════════════════════════════════════════
self.addEventListener('push', (event) => {
    let data = {};
    try {
        data = event.data ? event.data.json() : {};
    } catch (e) {
        data = { title: 'GroupPay', body: event.data ? event.data.text() : '' };
    }

    const title = data.title || 'GroupPay';
    const options = {
        body: data.body || '',
        icon: data.icon || '/static/img/icon-192.svg',
        badge: data.badge || '/static/img/icon-192.svg',
        data: { url: data.url || '/' },
        vibrate: [100, 50, 100],
        requireInteraction: false,
        tag: data.tag || 'grouppay-notification',
    };

    event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener('notificationclick', (event) => {
    event.notification.close();
    const url = (event.notification.data && event.notification.data.url) || '/';

    event.waitUntil(
        clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clientList) => {
            for (const client of clientList) {
                if (client.url === url && 'focus' in client) {
                    return client.focus();
                }
            }
            if (clients.openWindow) {
                return clients.openWindow(url);
            }
        })
    );
});
