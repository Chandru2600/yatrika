"""
Shared Pytest Fixtures and Configuration for Yatrika E2E Regression Testing
Provides isolated browser contexts, desktop & mobile viewports, and test utilities.
"""

import os
import sys
import uuid
import pytest
from playwright.sync_api import sync_playwright

BASE_URL = os.environ.get("YATRIKA_TEST_BASE_URL", "http://127.0.0.1:5001")


def get_browser_instance(p, headless=True):
    """
    Launch a Chromium-compatible browser with fallback across:
    1. System Google Chrome (installed on host)
    2. Bundled Playwright Chromium
    3. Microsoft Edge
    """
    for channel in ["chrome", None, "msedge"]:
        try:
            if channel:
                return p.chromium.launch(channel=channel, headless=headless)
            return p.chromium.launch(headless=headless)
        except Exception:
            continue
    raise RuntimeError("Failed to launch any Chromium-compatible browser.")


@pytest.fixture(scope="session")
def base_url():
    """Return the active base URL for test target."""
    return BASE_URL


@pytest.fixture(scope="session")
def playwright_instance():
    """Session-scoped Playwright runtime."""
    with sync_playwright() as p:
        yield p


@pytest.fixture(scope="session")
def browser(playwright_instance):
    """Session-scoped browser instance."""
    b = get_browser_instance(playwright_instance, headless=True)
    yield b
    b.close()


@pytest.fixture
def desktop_context(browser):
    """Desktop browser context (1280x800)."""
    ctx = browser.new_context(
        viewport={"width": 1280, "height": 800},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    yield ctx
    ctx.close()


@pytest.fixture
def mobile_context_375(browser):
    """Standard mobile browser context (375x667)."""
    ctx = browser.new_context(
        viewport={"width": 375, "height": 667},
        is_mobile=True,
        user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1"
    )
    yield ctx
    ctx.close()


@pytest.fixture
def mobile_context_320(browser):
    """Narrow mobile browser context (320x568 - iPhone SE 1st gen)."""
    ctx = browser.new_context(
        viewport={"width": 320, "height": 568},
        is_mobile=True,
        user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148"
    )
    yield ctx
    ctx.close()


# ── Test Utilities ────────────────────────────────────────────────────────────

def create_unique_user():
    uid = uuid.uuid4().hex[:8]
    return {
        "name": f"Traveler {uid}",
        "email": f"e2e_{uid}@yatrika.local",
        "password": "Password@123"
    }


def register_user(page, user_data, base_url=BASE_URL):
    page.goto(f"{base_url}/auth/register")
    page.fill('input[name="name"]', user_data["name"])
    page.fill('input[name="email"]', user_data["email"])
    page.fill('input[name="password"]', user_data["password"])
    page.fill('input[name="confirm_password"]', user_data["password"])
    page.check('input#agreeTerms')
    page.click('button[type="submit"]')
    page.wait_for_load_state("networkidle")


def login_user(page, user_data, base_url=BASE_URL):
    page.goto(f"{base_url}/auth/login")
    page.fill('input[name="email"]', user_data["email"])
    page.fill('input[name="password"]', user_data["password"])
    page.click('button[type="submit"]')
    page.wait_for_load_state("networkidle")


def create_wizard_trip(page, destination="Mysuru", origin="Bengaluru", days=3, budget=25000):
    payload = {
        "destination": destination,
        "source": origin,
        "start_date": "2026-11-10",
        "end_date": "2026-11-12",
        "num_days": days,
        "num_travelers": 2,
        "budget": budget,
        "travel_style": "heritage",
        "transport": "train",
        "transit_mode": "train",
        "transit_cost": 640,
        "selected_stay": {
            "name": f"Royal Heritage Palace {destination}",
            "price_per_night": 3500,
            "star_rating": 4.5,
            "address": f"Palace Road, {destination}"
        },
        "selected_attractions": [
            {"id": "s1", "name": f"{destination} Palace", "dur": "2h", "fee": 100, "lat": 12.305, "lon": 76.655},
            {"id": "s2", "name": f"{destination} Royal Gardens", "dur": "1.5h", "fee": 50, "lat": 12.310, "lon": 76.660},
            {"id": "s3", "name": f"{destination} Hill View", "dur": "2.5h", "fee": 0, "lat": 12.280, "lon": 76.670}
        ],
        "transit_details": {"mode": "train", "cost": 640},
        "dietary_preference": "vegetarian"
    }

    response = page.evaluate("""async (data) => {
        const res = await fetch('/planner/save_wizard', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(data)
        });
        return {
            status: res.status,
            json: await res.json()
        };
    }""", payload)

    assert response["status"] == 200, f"Trip creation failed: {response}"
    assert "trip_id" in response["json"], f"No trip_id in response: {response}"
    return response["json"]["trip_id"]
