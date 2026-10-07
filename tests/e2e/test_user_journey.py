"""Tests E2E - Parcours utilisateur."""
import pytest
from playwright.sync_api import expect

BASE = "http://127.0.0.1:8000"


@pytest.mark.e2e
def test_homepage_loads(page):
    response = page.goto(BASE)
    assert response.status == 200


@pytest.mark.e2e
def test_login_page(page):
    response = page.goto(f"{BASE}/admin/login/")
    assert response.status == 200
    expect(page.locator('input[name="username"]')).to_be_visible()


@pytest.mark.e2e
def test_health_endpoint(page):
    response = page.goto(f"{BASE}/health/")
    assert response.status == 200


@pytest.mark.e2e
def test_404_page(page):
    response = page.goto(f"{BASE}/unknown-xyz-abc/")
    assert response.status == 404
