"""Fixtures E2E Playwright."""
import os
import django
import pytest

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

BASE_URL = os.environ.get("E2E_BASE_URL", "http://127.0.0.1:8000")

# Identifiants du user de test (superuser seedé)
ADMIN_EMAIL = os.environ.get("E2E_ADMIN_EMAIL", "admin@sonabel-demo.com")
ADMIN_PASSWORD = os.environ.get("E2E_ADMIN_PASSWORD", "admin")


@pytest.fixture(scope="session")
def base_url():
    return BASE_URL


@pytest.fixture(scope="session")
def admin_credentials():
    return {"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    """Config navigateur."""
    return {
        **browser_context_args,
        "viewport": {"width": 1280, "height": 800},
        "ignore_https_errors": True,
        "locale": "fr-FR",
    }


@pytest.fixture
def login(page, base_url, admin_credentials):
    """Login automatique via /admin/login/."""
    page.goto(f"{base_url}/admin/login/")
    page.fill('input[name="username"]', admin_credentials["email"])
    page.fill('input[name="password"]', admin_credentials["password"])
    page.click('input[type="submit"]')
    # Attendre la redirection vers le site
    page.wait_for_url(f"{base_url}/**", timeout=10000)
    return page


@pytest.fixture
def logged_page(login):
    """Page deja authentifiee."""
    return login
