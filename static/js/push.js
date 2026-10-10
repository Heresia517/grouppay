// GroupPay Push Notifications — v4 (fix scope)
(function() {
    'use strict';

    console.log('[Push] 1. Script v4 charge');

    const VAPID_KEY_URL = '/api/push/vapid-key/';
    const SUBSCRIBE_URL = '/api/push/subscribe/';
    const UNSUBSCRIBE_URL = '/api/push/unsubscribe/';
    const SW_URL = '/sw.js';
    const SW_SCOPE = '/';

    // ═══════════════════════════════════════════════════════════
    // ENREGISTREMENT SERVICE WORKER (scope racine)
    // ═══════════════════════════════════════════════════════════
    async function ensureServiceWorker() {
        if (!('serviceWorker' in navigator)) {
            return { ok: false, error: 'Service Worker non supporte' };
        }

        try {
            // Desenregistrer les anciens SW (avec mauvais scope)
            const regs = await navigator.serviceWorker.getRegistrations();
            for (const reg of regs) {
                if (!reg.scope.endsWith('://127.0.0.1:8000/') && !reg.scope.endsWith('://localhost:8000/')) {
                    console.log('[Push] Desenregistrement ancien SW:', reg.scope);
                    await reg.unregister();
                }
            }

            // Enregistrer le nouveau avec scope /
            const reg = await navigator.serviceWorker.register(SW_URL, { scope: SW_SCOPE });
            console.log('[Push] SW enregistre:', reg.scope);

            // Attendre qu'il soit pret
            await navigator.serviceWorker.ready;
            console.log('[Push] SW pret');

            return { ok: true, registration: reg };
        } catch (e) {
            console.error('[Push] Erreur SW:', e);
            return { ok: false, error: e.message };
        }
    }

    // ═══════════════════════════════════════════════════════════
    // HELPERS
    // ═══════════════════════════════════════════════════════════
    function urlBase64ToUint8Array(base64String) {
        const padding = '='.repeat((4 - base64String.length % 4) % 4);
        const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
        const rawData = window.atob(base64);
        const outputArray = new Uint8Array(rawData.length);
        for (let i = 0; i < rawData.length; ++i) {
            outputArray[i] = rawData.charCodeAt(i);
        }
        return outputArray;
    }

    function getCsrfToken() {
        const match = document.cookie.match(/csrftoken=([^;]+)/);
        return match ? match[1] : '';
    }

    async function getVapidKey() {
        const r = await fetch(VAPID_KEY_URL);
        const data = await r.json();
        return data.publicKey;
    }

    async function requestPermission() {
        if (Notification.permission === 'granted') return true;
        if (Notification.permission === 'denied') return false;
        return (await Notification.requestPermission()) === 'granted';
    }

    // ═══════════════════════════════════════════════════════════
    // SUBSCRIBE
    // ═══════════════════════════════════════════════════════════
    async function subscribeUser() {
        try {
            console.log('[Push] === SUBSCRIBE START ===');

            // 1. SW
            const sw = await ensureServiceWorker();
            if (!sw.ok) return { ok: false, error: sw.error };

            // 2. Support
            if (!('PushManager' in window)) {
                return { ok: false, error: 'PushManager non supporte' };
            }

            // 3. Permission
            const granted = await requestPermission();
            if (!granted) {
                return { ok: false, error: 'Permission refusee' };
            }

            // 4. VAPID
            const publicKey = await getVapidKey();
            if (!publicKey) {
                return { ok: false, error: 'Cle VAPID absente' };
            }
            console.log('[Push] Cle VAPID OK');

            // 5. Subscribe
            const reg = await navigator.serviceWorker.ready;
            let sub = await reg.pushManager.getSubscription();
            if (sub) {
                console.log('[Push] Deja abonne, on retire...');
                await sub.unsubscribe();
            }

            sub = await reg.pushManager.subscribe({
                userVisibleOnly: true,
                applicationServerKey: urlBase64ToUint8Array(publicKey),
            });
            console.log('[Push] Subscription creee');

            // 6. Envoi au serveur
            const r = await fetch(SUBSCRIBE_URL, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken(),
                },
                body: JSON.stringify(sub.toJSON()),
            });

            console.log('[Push] Status HTTP:', r.status);

            if (!r.ok) {
                return { ok: false, error: 'Erreur serveur ' + r.status };
            }

            const result = await r.json();
            console.log('[Push] === SUCCESS ===', result);
            return { ok: true, subscription: sub, server: result };

        } catch (e) {
            console.error('[Push] XX ERREUR:', e);
            return { ok: false, error: e.message };
        }
    }

    // ═══════════════════════════════════════════════════════════
    // UNSUBSCRIBE
    // ═══════════════════════════════════════════════════════════
    async function unsubscribeUser() {
        try {
            const reg = await navigator.serviceWorker.ready;
            const sub = await reg.pushManager.getSubscription();
            if (!sub) return { ok: true, action: 'not_subscribed' };

            await fetch(UNSUBSCRIBE_URL, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken(),
                },
                body: JSON.stringify({ endpoint: sub.endpoint }),
            });

            await sub.unsubscribe();
            return { ok: true, action: 'unsubscribed' };
        } catch (e) {
            return { ok: false, error: e.message };
        }
    }

    async function isSubscribed() {
        if (!('serviceWorker' in navigator)) return false;
        try {
            const reg = await navigator.serviceWorker.ready;
            const sub = await reg.pushManager.getSubscription();
            return !!sub;
        } catch (e) {
            return false;
        }
    }

    async function checkSupport() {
        return {
            ok: 'serviceWorker' in navigator && 'PushManager' in window && 'Notification' in window,
            serviceWorker: 'serviceWorker' in navigator,
            PushManager: 'PushManager' in window,
            Notification: 'Notification' in window,
            permission: Notification.permission,
        };
    }

    // ═══════════════════════════════════════════════════════════
    // API PUBLIQUE
    // ═══════════════════════════════════════════════════════════
    window.GroupPayPush = {
        subscribe: subscribeUser,
        unsubscribe: unsubscribeUser,
        isSubscribed: isSubscribed,
        checkSupport: checkSupport,
        ensureServiceWorker: ensureServiceWorker,

        async toggle() {
            if (await isSubscribed()) {
                await unsubscribeUser();
                return { ok: false, action: 'unsubscribed' };
            }
            return await subscribeUser();
        },
    };

    console.log('[Push] GroupPayPush v4 pret');
})();
