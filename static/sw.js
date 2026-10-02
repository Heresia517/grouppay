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
