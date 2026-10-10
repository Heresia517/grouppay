"""Tests E2E Auth + securite."""
import pytest


@pytest.mark.e2e
class TestAuth:
    def test_login_required_redirects(self, page, base_url):
        """Sans login, on est redirige vers la page admin."""
        response = page.goto(f"{base_url}/da/")
        # Soit redirection vers /admin/login/, soit contenu login
        assert "/admin/login" in page.url or "login" in page.url.lower() or response.status == 302

    def test_login_works(self, login, base_url):
        """Login reussi."""
        assert "/admin" not in login.url or login.url == f"{base_url}/" or "login" not in login.url.lower()

    def test_logout_redirects(self, logged_page, base_url):
        logged_page.goto(f"{base_url}/admin/logout/")
        # Apres logout, on doit etre sur la page de login ou accueil
        assert "logout" not in logged_page.url.lower() or "login" in logged_page.url.lower()


@pytest.mark.e2e
class TestSecurity:
    def test_health_endpoint(self, page, base_url):
        """L'endpoint /health/ est public."""
        response = page.goto(f"{base_url}/health/")
        assert response.status == 200

    def test_vapid_key_public(self, page, base_url):
        """La cle VAPID est publique."""
        response = page.goto(f"{base_url}/api/push/vapid-key/")
        assert response.status == 200

    def test_404_page(self, page, base_url):
        """Page inexistante retourne 404."""
        response = page.goto(f"{base_url}/this-page-doesnt-exist-xyz123/")
        assert response.status == 404

    def test_sw_js_accessible(self, page, base_url):
        """Service Worker accessible."""
        response = page.goto(f"{base_url}/sw.js")
        assert response.status == 200

    def test_sw_v4_js_accessible(self, page, base_url):
        response = page.goto(f"{base_url}/sw-v4.js")
        assert response.status == 200

    def test_manifest_accessible(self, page, base_url):
        response = page.goto(f"{base_url}/static/manifest.webmanifest")
        assert response.status == 200
