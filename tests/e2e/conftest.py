import os
import django
import pytest

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
django.setup()

BASE_URL = os.environ.get("E2E_BASE_URL", "http://127.0.0.1:8000")


@pytest.fixture(scope="session")
def base_url():
    return BASE_URL


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    return {**browser_context_args, "viewport": {"width": 1280, "height": 720}}


@pytest.fixture
def logged_in_page(page, base_url):
    page.goto(f"{base_url}/admin/login/")
    page.fill('input[name="username"]', "admin@sonabel-demo.com")
    page.fill('input[name="password"]', "admin")
    page.click('input[type="submit"]')
    page.wait_for_url(f"{base_url}/**", timeout=5000)
    return page
