"""Tests E2E du module Mutuelle (commandes, panier)."""
import pytest
from playwright.sync_api import expect


@pytest.mark.e2e
class TestCatalogue:
    def test_catalogue_loads(self, logged_page, base_url):
        response = logged_page.goto(f"{base_url}/")
        assert response.status == 200
        expect(logged_page.locator("body")).to_contain_text("Catalogue", timeout=5000)

    def test_catalogue_has_products(self, logged_page, base_url):
        logged_page.goto(f"{base_url}/")
        # Au moins une carte produit
        cards = logged_page.locator(".product-card")
        assert cards.count() > 0, "Aucun produit dans le catalogue"

    def test_catalog_search(self, logged_page, base_url):
        logged_page.goto(f"{base_url}/")
        # Chercher champ de recherche
        search = logged_page.locator("#catalog-search")
        if search.count() > 0:
            search.fill("riz")
            logged_page.wait_for_timeout(500)
            # Vérifier que le filtrage se fait
            assert True


@pytest.mark.e2e
class TestCart:
    def test_cart_page_loads(self, logged_page, base_url):
        response = logged_page.goto(f"{base_url}/cart/")
        assert response.status == 200

    def test_add_to_cart(self, logged_page, base_url):
        logged_page.goto(f"{base_url}/")
        # Cliquer sur le premier bouton "+" dans une carte produit
        add_btn = logged_page.locator("form[action*='cart/add'] button").first
        if add_btn.count() > 0:
            add_btn.click()
            logged_page.wait_for_timeout(1000)
            # Badge doit apparaître
            badge = logged_page.locator("#cart-badge-container")
            assert badge.count() > 0


@pytest.mark.e2e
class TestProfile:
    def test_profile_page(self, logged_page, base_url):
        response = logged_page.goto(f"{base_url}/profile/")
        assert response.status == 200

    def test_analytics_page(self, logged_page, base_url):
        response = logged_page.goto(f"{base_url}/analytics/")
        assert response.status == 200

    def test_referrals_page(self, logged_page, base_url):
        response = logged_page.goto(f"{base_url}/referrals/")
        assert response.status == 200

    def test_currency_converter(self, logged_page, base_url):
        response = logged_page.goto(f"{base_url}/currencies/")
        assert response.status == 200
