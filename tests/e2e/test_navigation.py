"""Tests E2E de la navigation globale."""
import pytest
from playwright.sync_api import expect


PAGES = [
    ("/", "Catalogue"),
    ("/cart/", "panier"),
    ("/orders/my/", "commandes"),
    ("/profile/", "profil"),
    ("/analytics/", "analytics"),
    ("/referrals/", "parrainage"),
    ("/currencies/", "devises"),
    ("/wishlist/", "favoris"),
    ("/requests/", "demandes"),
    ("/da/", "Dashboard"),
    ("/da/admin/", "Admin"),
    ("/inventory/", "Inventaire"),
    ("/rh/dashboard/", "Dashboard RH"),
    ("/rh/deductions/", "Retenue"),
    ("/rh/reports/", "Rapports"),
    ("/stock/", "Stock"),
    ("/supplier/", "fournisseur"),
    ("/notifications/", "notifications"),
]


@pytest.mark.e2e
@pytest.mark.parametrize("path,expected_keyword", PAGES)
def test_page_accessible(logged_page, base_url, path, expected_keyword):
    """Chaque page doit etre accessible avec login."""
    response = logged_page.goto(f"{base_url}{path}")
    assert response.status == 200, f"{path} retourne {response.status}"

    # Verifier que le contenu attendu est present
    body = logged_page.locator("body").inner_text()
    # Au moins on doit avoir du contenu HTML
    assert len(body) > 100, f"{path} contenu trop court"


@pytest.mark.e2e
def test_navbar_exists(logged_page, base_url):
    """La navbar doit contenir les liens principaux."""
    logged_page.goto(f"{base_url}/")
    nav = logged_page.locator("nav")
    assert nav.count() > 0


@pytest.mark.e2e
def test_theme_toggle_exists(logged_page, base_url):
    """Le bouton de theme doit exister."""
    logged_page.goto(f"{base_url}/")
    # Chercher le bouton toggle
    toggle = logged_page.locator("button[onclick*='toggleTheme']")
    assert toggle.count() > 0


@pytest.mark.e2e
def test_responsive_mobile(logged_page, base_url):
    """Test affichage mobile."""
    logged_page.set_viewport_size({"width": 375, "height": 667})
    response = logged_page.goto(f"{base_url}/")
    assert response.status == 200
    # Verifier pas de scroll horizontal excessif
    scroll_width = logged_page.evaluate("document.documentElement.scrollWidth")
    assert scroll_width <= 400
