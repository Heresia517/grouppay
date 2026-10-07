"""Tests E2E - Parcours RH."""
import pytest
from playwright.sync_api import expect

BASE = "http://127.0.0.1:8000"


@pytest.mark.e2e
def test_rh_dashboard(logged_in_page):
    response = logged_in_page.goto(f"{BASE}/rh/dashboard/")
    assert response.status == 200


@pytest.mark.e2e
def test_stock_dashboard(logged_in_page):
    response = logged_in_page.goto(f"{BASE}/stock/")
    assert response.status == 200


@pytest.mark.e2e
def test_import_members(logged_in_page):
    response = logged_in_page.goto(f"{BASE}/rh/members/import/")
    assert response.status == 200
