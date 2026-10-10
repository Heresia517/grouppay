"""Tests E2E du module Demande d'Achat."""
import pytest
from playwright.sync_api import expect


@pytest.mark.e2e
class TestDADashboard:
    def test_dashboard_loads(self, logged_page, base_url):
        response = logged_page.goto(f"{base_url}/da/")
        assert response.status == 200
        expect(logged_page.locator("body")).to_contain_text("Dashboard DA", timeout=5000)

    def test_stats_page(self, logged_page, base_url):
        response = logged_page.goto(f"{base_url}/da/stats/")
        assert response.status == 200

    def test_admin_page(self, logged_page, base_url):
        response = logged_page.goto(f"{base_url}/da/admin/")
        assert response.status == 200

    def test_items_catalog(self, logged_page, base_url):
        response = logged_page.goto(f"{base_url}/da/items/")
        assert response.status == 200

    def test_categories_admin(self, logged_page, base_url):
        response = logged_page.goto(f"{base_url}/da/admin/categories/")
        assert response.status == 200

    def test_directions_admin(self, logged_page, base_url):
        response = logged_page.goto(f"{base_url}/da/admin/directions/")
        assert response.status == 200

    def test_services_admin(self, logged_page, base_url):
        response = logged_page.goto(f"{base_url}/da/admin/services/")
        assert response.status == 200


@pytest.mark.e2e
class TestDAWorkflow:
    def test_create_da_form(self, logged_page, base_url):
        response = logged_page.goto(f"{base_url}/da/requests/new/")
        assert response.status == 200
        expect(logged_page.locator("body")).to_contain_text("Nouvelle Demande", timeout=3000)

    def test_da_list(self, logged_page, base_url):
        response = logged_page.goto(f"{base_url}/da/requests/")
        assert response.status == 200

    def test_da_export_excel(self, logged_page, base_url):
        response = logged_page.goto(f"{base_url}/da/export/excel/")
        assert response.status == 200
        # Verifier le Content-Type
        content_type = response.headers.get("content-type", "")
        assert "spreadsheet" in content_type or "excel" in content_type
