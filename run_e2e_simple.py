"""Tests E2E simples sans Playwright — via requests."""
import os
import sys
import requests

BASE_URL = os.environ.get("E2E_BASE_URL", "http://127.0.0.1:8000")
ADMIN_EMAIL = os.environ.get("E2E_ADMIN_EMAIL", "admin@sonabel-demo.com")
ADMIN_PASSWORD = os.environ.get("E2E_ADMIN_PASSWORD", "admin123")


def log_ok(msg): print(f"  OK  {msg}")
def log_err(msg): print(f"  XX  {msg}")


def get_session():
    """Login via /admin/login/ avec cookies + CSRF."""
    s = requests.Session()

    # 1. GET login page pour obtenir le CSRF token
    r = s.get(f"{BASE_URL}/admin/login/")
    import re
    m = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', r.text)
    if not m:
        # Essaye avec cookie
        csrf = s.cookies.get("csrftoken", "")
    else:
        csrf = m.group(1)

    # 2. POST login
    r = s.post(
        f"{BASE_URL}/admin/login/",
        data={
            "username": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD,
            "csrfmiddlewaretoken": csrf,
            "next": "/",
        },
        headers={"Referer": f"{BASE_URL}/admin/login/"},
        allow_redirects=True,
    )

    return s


def test_page(session, path, expected_status=200, must_contain=None):
    try:
        r = session.get(f"{BASE_URL}{path}", timeout=10, allow_redirects=False)
        if r.status_code != expected_status:
            log_err(f"{path} -> {r.status_code} (attendu {expected_status})")
            return False
        if must_contain and must_contain.lower() not in r.text.lower():
            log_err(f"{path} -> contenu '{must_contain}' absent")
            return False
        log_ok(f"{path} -> {r.status_code}")
        return True
    except Exception as e:
        log_err(f"{path} -> {e}")
        return False


def main():
    print()
    print("=" * 72)
    print("  GROUPPAY TESTS SIMPLES")
    print("=" * 72)
    print()

    # Health
    try:
        r = requests.get(f"{BASE_URL}/health/", timeout=5)
        if r.status_code != 200:
            log_err(f"Serveur KO ({r.status_code})")
            sys.exit(1)
        log_ok("Serveur Django accessible")
    except Exception as e:
        log_err(f"Serveur inaccessible : {e}")
        print("  Lance : python manage.py runserver")
        sys.exit(1)

    print()
    print(">>> Endpoints publics")
    s_anon = requests.Session()
    test_page(s_anon, "/health/", 200)
    test_page(s_anon, "/api/push/vapid-key/", 200)
    test_page(s_anon, "/sw.js", 200)
    test_page(s_anon, "/sw-v4.js", 200)
    test_page(s_anon, "/page-inexistante-xyz/", 404)

    print()
    print(">>> Login + Session")
    s = get_session()

    # Verifier le login
    r = s.get(f"{BASE_URL}/admin/", allow_redirects=False)
    if r.status_code == 200:
        log_ok(f"Login OK ({ADMIN_EMAIL})")
    else:
        log_err(f"Login echoue - status {r.status_code}")

    print()
    print(">>> Pages authentifiees")
    pages = [
        "/", "/cart/", "/orders/my/", "/profile/", "/analytics/",
        "/referrals/", "/currencies/", "/wishlist/", "/requests/",
        "/da/", "/da/admin/", "/da/stats/", "/inventory/",
        "/rh/dashboard/", "/rh/deductions/", "/rh/reports/",
        "/stock/", "/supplier/", "/push-v5/", "/notifications/",
    ]
    passed = 0
    for path in pages:
        if test_page(s, path, 200):
            passed += 1

    print()
    print("=" * 72)
    print(f"  RESULTAT : {passed}/{len(pages)} pages OK")
    print("=" * 72)
    print()


if __name__ == "__main__":
    main()
