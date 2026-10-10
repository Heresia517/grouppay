"""Tests E2E du module RH."""
import pytest
from playwright.sync_api import expect


@pytest.mark.e2e
class TestRHDashboard:
    def test_dashboard(self, logged_page, base_url):
        response = logged_page.goto(f"{base_url}/rh/dashboard/")
        assert response.status == 200
        expect(logged_page.locator("body")).to_contain_text("Dashboard RH", timeout=5000)

    def test_deductions_page(self, logged_page, base_url):
        response = logged_page.goto(f"{base_url}/rh/deductions/")
        assert response.status == 200

    def test_import_members(self, logged_page, base_url):
        response = logged_page.goto(f"{base_url}/rh/members/import/")
        assert response.status == 200

    def test_abandoned_carts(self, logged_page, base_url):
        response = logged_page.goto(f"{base_url}/rh/abandoned-carts/")
        assert response.status == 200

    def test_reports_list(self, logged_page, base_url):
        response = logged_page.goto(f"{base_url}/rh/reports/")
        assert response.status == 200

    def test_suppliers_overview(self, logged_page, base_url):
        response = logged_page.goto(f"{base_url}/rh/suppliers/")
        assert response.status == 200

    def test_stock_dashboard(self, logged_page, base_url):
        response = logged_page.goto(f"{base_url}/stock/")
        assert response.status == 200


@pytest.mark.e2e
class TestRHExport:
    def test_export_dashboard_excel(self, logged_page, base_url):
        response = logged_page.goto(f"{base_url}/rh/dashboard/export/")
        assert response.status == 200
        ct = response.headers.get("content-type", "")
        assert "spreadsheet" in ct or "excel" in ct

    def test_export_dashboard_pdf(self, logged_page, base_url):
        response = logged_page.goto(f"{base_url}/rh/dashboard/export-pdf/")
        assert response.status == 200
        ct = response.headers.get("content-type", "")
        assert "pdf" in ct
