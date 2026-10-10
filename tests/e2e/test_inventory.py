"""Tests E2E du module Inventaire."""
import pytest
from playwright.sync_api import expect


@pytest.mark.e2e
class TestInventory:
    def test_dashboard_loads(self, logged_page, base_url):
        response = logged_page.goto(f"{base_url}/inventory/")
        assert response.status == 200
        expect(logged_page.locator("body")).to_contain_text("Inventaire", timeout=5000)

    def test_asset_list(self, logged_page, base_url):
        response = logged_page.goto(f"{base_url}/inventory/assets/")
        assert response.status == 200

    def test_asset_create_form(self, logged_page, base_url):
        response = logged_page.goto(f"{base_url}/inventory/assets/new/")
        assert response.status == 200

    def test_seeded_assets_visible(self, logged_page, base_url):
        logged_page.goto(f"{base_url}/inventory/assets/")
        # Au moins un asset seedé visible
        body_text = logged_page.locator("body").inner_text()
        # Cherche des noms seedés
        assert any(name in body_text for name in ["Ordinateur", "Bureau", "Toyota", "Climatiseur"])
