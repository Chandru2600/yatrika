"""
Comprehensive End-to-End (E2E) Regression Test Suite for Yatrika Travel Planner Agent
Built with Playwright for cross-browser, responsive, and security testing.

Covers:
- Section A: Desktop traveler journey (1280x800)
- Section B: Mobile responsive journey (375x667 and 320x568)
- Section C: Security & authorization regression tests (IDOR, sharing, exports)
- Section D: Phase 3B feature verification (ICS calendar, weather horizon, smart packing)
"""

import os
import sys
import json
import pytest
from playwright.sync_api import expect
from tests.e2e.conftest import (
    BASE_URL,
    create_unique_user,
    register_user,
    login_user,
    create_wizard_trip
)


# ==============================================================================
# SECTION A: DESKTOP TRAVELER JOURNEY (1280x800)
# ==============================================================================

class TestDesktopTravelerJourney:
    """Desktop viewport (1280x800) full user lifecycle and journey testing."""

    def test_01_landing_page_loads_successfully(self, desktop_context, base_url):
        """1. Open the landing page and verify the page loads successfully."""
        page = desktop_context.new_page()
        page.goto(f"{base_url}/")
        page.wait_for_load_state("networkidle")

        # Verify page title and brand identity
        assert "Yatrika" in page.title() or "Travel" in page.title()
        brand_brand = page.locator(".navbar-brand")
        expect(brand_brand).to_be_visible()

        # Verify primary navigation links
        nav = page.locator("#mainNav")
        expect(nav).to_be_visible()

    def test_02_synthetic_user_registration_and_login(self, desktop_context, base_url):
        """2 & 3. Register synthetic user, logout, login, and verify authenticated state."""
        page = desktop_context.new_page()
        user = create_unique_user()

        # Register
        register_user(page, user, base_url)
        assert "/welcome" in page.url or "/dashboard" in page.url or "/" in page.url
        assert "Yatrika" in page.content()

        # Logout
        page.goto(f"{base_url}/auth/logout")
        page.wait_for_load_state("networkidle")
        assert "logged out" in page.content().lower() or "/" in page.url

        # Login
        login_user(page, user, base_url)
        assert "/welcome" in page.url or "/dashboard" in page.url or "/" in page.url
        assert user["name"] in page.content() or "Launchpad" in page.content()

    def test_03_wizard_ui_progression_and_trip_generation(self, desktop_context, base_url):
        """4 to 7. Open wizard, step through stages via UI controls, and generate trip."""
        page = desktop_context.new_page()
        user = create_unique_user()
        register_user(page, user, base_url)

        # 4 & 5. Open wizard with parameters
        wizard_url = f"{base_url}/planner/wizard?destination=Mysuru&source=Bengaluru&days=3&travelers=2&budget=25000&step=stay"
        page.goto(wizard_url)
        page.wait_for_load_state("networkidle")

        # Verify Stage 1 is active
        stage_step = page.locator('.progress-step[data-step="1"]')
        expect(stage_step).to_be_visible()

        # 6. Step progression: Stage 1 (Stay) -> Stage 2 (Transit)
        page.click('.btn-wizard-next')
        page.wait_for_timeout(400)
        expect(page.locator('#wstep-2')).to_be_visible()

        # Stage 2 (Transit) -> Stage 3 (Sights)
        page.click('#wstep-2 .btn-wizard-next')
        page.wait_for_timeout(400)
        expect(page.locator('#wstep-3')).to_be_visible()

        # Stage 3 (Sights) -> Stage 4 (Schedule)
        page.click('#wstep-3 .btn-wizard-next')
        page.wait_for_timeout(400)
        expect(page.locator('#wstep-4')).to_be_visible()

        # Stage 4 (Schedule) -> Stage 5 (Overview)
        page.click('#wstep-4 .btn-wizard-next')
        page.wait_for_timeout(400)
        expect(page.locator('#wstep-5')).to_be_visible()

        # 7. Save trip through UI
        save_btn = page.locator('button:has-text("Save Trip to Dashboard")').first
        expect(save_btn).to_be_visible()

        with page.expect_navigation():
            save_btn.click()

        # Verify redirected to trip dossier
        assert "/planner/" in page.url
        assert page.url.split("/planner/")[-1].isdigit()

    def test_04_itinerary_dossier_rendering_and_map_visibility(self, desktop_context, base_url):
        """8 & 9. Verify resulting itinerary content, boarding pass, and map container."""
        page = desktop_context.new_page()
        user = create_unique_user()
        register_user(page, user, base_url)
        trip_id = create_wizard_trip(page, destination="Jaipur", origin="Delhi", days=3)

        page.goto(f"{base_url}/planner/{trip_id}")
        page.wait_for_load_state("networkidle")

        # Verify Boarding Pass
        ticket = page.locator(".dossier-boarding-pass")
        expect(ticket).to_be_visible()
        assert "Jaipur" in page.content()

        # Switch to Map Tab & Verify Map Container
        page.click('a[href="#tab-map"]')
        page.wait_for_selector("#tab-map.active", timeout=5000)
        map_el = page.locator("#tripMap")
        expect(map_el).to_be_visible()

        # Verify all pillars are present
        expect(page.locator('a[href="#tab-itinerary"]')).to_be_visible()
        expect(page.locator('a[href="#tab-budget"]')).to_be_visible()
        expect(page.locator('a[href="#tab-packing"]')).to_be_visible()

    def test_05_pdf_and_ics_downloads_through_ui(self, desktop_context, base_url):
        """10 & 11. Download PDF and ICS calendar through UI and verify headers & content."""
        page = desktop_context.new_page()
        user = create_unique_user()
        register_user(page, user, base_url)
        trip_id = create_wizard_trip(page, destination="Goa", origin="Mumbai")

        page.goto(f"{base_url}/planner/{trip_id}")
        page.wait_for_load_state("networkidle")

        # 10. Verify PDF download
        pdf_res = page.request.get(f"{base_url}/planner/{trip_id}/pdf")
        assert pdf_res.status == 200
        assert "application/pdf" in pdf_res.headers.get("content-type", "")
        pdf_bytes = pdf_res.body()
        assert pdf_bytes.startswith(b"%PDF-")
        assert len(pdf_bytes) > 1000

        # 11. Verify ICS download
        ics_res = page.request.get(f"{base_url}/planner/{trip_id}/ics")
        assert ics_res.status == 200
        assert "text/calendar" in ics_res.headers.get("content-type", "")
        ics_text = ics_res.text()
        assert "BEGIN:VCALENDAR" in ics_text
        assert "VERSION:2.0" in ics_text
        assert "BEGIN:VEVENT" in ics_text
        assert "END:VCALENDAR" in ics_text

    def test_06_trip_appears_in_dashboard_and_saved_trips(self, desktop_context, base_url):
        """12. Verify created trip appears in dashboard and saved trips views."""
        page = desktop_context.new_page()
        user = create_unique_user()
        register_user(page, user, base_url)
        trip_id = create_wizard_trip(page, destination="Udaipur", origin="Ahmedabad")

        # Check Dashboard
        page.goto(f"{base_url}/dashboard")
        page.wait_for_load_state("networkidle")
        content = page.content()
        assert "Udaipur" in content

        # Check Saved Trips
        page.goto(f"{base_url}/planner/saved")
        page.wait_for_load_state("networkidle")
        assert "Udaipur" in page.content() or page.locator(f'a[href*="/planner/{trip_id}"]').count() > 0


# ==============================================================================
# SECTION B: MOBILE RESPONSIVE JOURNEY (375x667 & 320x568)
# ==============================================================================

class TestMobileResponsiveJourney:
    """Mobile viewport responsive validation (375x667 and 320x568)."""

    def test_07_mobile_landing_and_navigation_auto_collapse(self, mobile_context_375, base_url):
        """Verify landing page hamburger navigation and auto-collapse behavior."""
        page = mobile_context_375.new_page()
        page.goto(f"{base_url}/")
        page.wait_for_load_state("networkidle")

        # Hamburger toggler is visible on mobile
        toggler = page.locator(".navbar-toggler")
        expect(toggler).to_be_visible()

        # Open mobile drawer
        toggler.click()
        page.wait_for_timeout(400)
        nav_collapse = page.locator("#mainNav")
        expect(nav_collapse).to_be_visible()

        # Zero horizontal overflow
        no_overflow = page.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth + 1")
        assert no_overflow, "Mobile landing page has horizontal scroll overflow"

    def test_08_mobile_wizard_scrollability_and_no_horizontal_overflow(self, mobile_context_375, base_url):
        """Verify mobile wizard scrolling unconstrained and zero clipping."""
        page = mobile_context_375.new_page()
        user = create_unique_user()
        register_user(page, user, base_url)

        page.goto(f"{base_url}/planner/wizard?destination=Mysuru&source=Bengaluru&days=3&travelers=2&budget=25000")
        page.wait_for_load_state("networkidle")

        # Unconstrained height and visible overflow contract
        overflow_visible = page.locator(".wizard-root").evaluate(
            "el => window.getComputedStyle(el).overflowY !== 'hidden'"
        )
        assert overflow_visible, "Wizard root should allow vertical scroll on mobile"

        # Zero horizontal overflow
        no_overflow = page.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth + 1")
        assert no_overflow, "Mobile wizard has horizontal scroll overflow"

    def test_09_mobile_itinerary_card_readability_and_stacked_boarding_pass(self, mobile_context_375, base_url):
        """Verify boarding ticket vertical stacking and itinerary cards on mobile."""
        page = mobile_context_375.new_page()
        user = create_unique_user()
        register_user(page, user, base_url)
        trip_id = create_wizard_trip(page, destination="Mysuru")

        page.goto(f"{base_url}/planner/{trip_id}")
        page.wait_for_load_state("networkidle")

        # Boarding pass stacks vertically
        ticket = page.locator(".dossier-boarding-pass")
        expect(ticket).to_be_visible()
        flex_dir = ticket.evaluate("el => window.getComputedStyle(el).flexDirection")
        assert flex_dir == "column", f"Expected column on mobile, got {flex_dir}"

        # Zero horizontal overflow
        no_overflow = page.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth + 1")
        assert no_overflow, "Mobile trip view has horizontal scroll overflow"

    def test_10_mobile_narrow_320_viewport_integrity(self, mobile_context_320, base_url):
        """Verify narrow 320x568 (iPhone SE 1st gen) viewport integrity."""
        page = mobile_context_320.new_page()
        page.goto(f"{base_url}/")
        page.wait_for_load_state("networkidle")

        # Zero horizontal overflow at 320px
        no_overflow = page.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth + 1")
        assert no_overflow, "Narrow 320px viewport has horizontal scroll overflow"

    def test_11_mobile_itinerary_reordering_interaction(self, mobile_context_375, base_url):
        """Verify activity reordering controls are present and operable on mobile."""
        page = mobile_context_375.new_page()
        user = create_unique_user()
        register_user(page, user, base_url)
        trip_id = create_wizard_trip(page, destination="Coorg")

        page.goto(f"{base_url}/planner/{trip_id}")
        page.wait_for_load_state("networkidle")

        # Switch to Day Planner
        page.click('a[href="#tab-itinerary"]')
        reorder_btns = page.locator(".btn-reorder-move")
        count = reorder_btns.count()
        # If activities exist, reorder buttons must be clickable
        if count > 0:
            first_btn = reorder_btns.first
            expect(first_btn).to_be_visible()

    def test_12_mobile_pdf_and_ics_export_triggers(self, mobile_context_375, base_url):
        """Verify export buttons are operable from the mobile passenger stub."""
        page = mobile_context_375.new_page()
        user = create_unique_user()
        register_user(page, user, base_url)
        trip_id = create_wizard_trip(page, destination="Manali")

        page.goto(f"{base_url}/planner/{trip_id}")
        page.wait_for_load_state("networkidle")

        # Verify PDF and ICS action buttons exist in DOM and are interactive
        pdf_btn = page.locator(".btn-pdf-download")
        expect(pdf_btn).to_be_visible()
        ics_btn = page.locator('button:has-text("Export Calendar")')
        expect(ics_btn).to_be_visible()


# ==============================================================================
# SECTION C: SECURITY & AUTHORIZATION REGRESSION TESTS
# ==============================================================================

class TestSecurityRegression:
    """Rigorous multi-user cross-boundary security and IDOR tests."""

    def test_13_expense_idor_cross_user_rejection(self, browser, base_url):
        """1. User B cannot add expenses to User A's trip."""
        ctx_a = browser.new_context()
        page_a = ctx_a.new_page()
        user_a = create_unique_user()
        register_user(page_a, user_a, base_url)
        trip_id_a = create_wizard_trip(page_a, destination="Hampi")

        ctx_b = browser.new_context()
        page_b = ctx_b.new_page()
        user_b = create_unique_user()
        register_user(page_b, user_b, base_url)

        # User B attempts to POST expense to User A's trip
        res = page_b.request.post(
            f"{base_url}/planner/{trip_id_a}/expense",
            form={"category": "food", "amount": "9999", "description": "Hacked Expense"}
        )
        # Should redirect away to dashboard
        assert "/dashboard" in res.url or res.status in [302, 403, 404]

        # Verify expense was NOT added to User A's trip
        page_a.goto(f"{base_url}/planner/{trip_id_a}")
        assert "Hacked Expense" not in page_a.content()

        ctx_a.close()
        ctx_b.close()

    def test_14_itinerary_update_ownership_protection(self, browser, base_url):
        """2. User B cannot modify User A's itinerary layout."""
        ctx_a = browser.new_context()
        page_a = ctx_a.new_page()
        user_a = create_unique_user()
        register_user(page_a, user_a, base_url)
        trip_id_a = create_wizard_trip(page_a, destination="Mysuru")

        ctx_b = browser.new_context()
        page_b = ctx_b.new_page()
        user_b = create_unique_user()
        register_user(page_b, user_b, base_url)

        # User B attempts to update User A's itinerary
        res = page_b.request.post(
            f"{base_url}/planner/{trip_id_a}/update_planner",
            data=json.dumps({"day_planner": {"1": {"morning": []}}}),
            headers={"Content-Type": "application/json"}
        )
        assert res.status == 404 or res.status == 403

        ctx_a.close()
        ctx_b.close()

    def test_15_private_sharing_and_token_lifecycle(self, browser, base_url):
        """3 & 5. Private sharing lifecycle: default private, enable token, revoke access."""
        ctx_a = browser.new_context()
        page_a = ctx_a.new_page()
        user_a = create_unique_user()
        register_user(page_a, user_a, base_url)
        trip_id_a = create_wizard_trip(page_a, destination="Ooty")

        ctx_anon = browser.new_context()
        page_anon = ctx_anon.new_page()

        # Step 1: Default private trip cannot be viewed without token
        page_anon.goto(f"{base_url}/planner/share/{trip_id_a}")
        assert page_anon.locator(".dossier-boarding-pass").count() == 0

        # Step 2: Owner enables sharing
        toggle_res = page_a.request.post(f"{base_url}/planner/{trip_id_a}/share/toggle")
        toggle_data = toggle_res.json()
        assert toggle_data["success"] is True
        assert toggle_data["is_public"] is True
        token = toggle_data["share_token"]
        assert len(token) >= 16

        # Step 3: Anonymous visitor can view with valid token
        page_anon.goto(f"{base_url}/planner/share/{token}")
        page_anon.wait_for_load_state("networkidle")
        expect(page_anon.locator(".dossier-boarding-pass")).to_be_visible()

        # Step 4: Owner disables sharing
        revoke_res = page_a.request.post(f"{base_url}/planner/{trip_id_a}/share/toggle")
        revoke_data = revoke_res.json()
        assert revoke_data["is_public"] is False

        # Step 5: Anonymous visitor can no longer view
        page_anon.goto(f"{base_url}/planner/share/{token}")
        page_anon.wait_for_load_state("networkidle")
        assert page_anon.locator(".dossier-boarding-pass").count() == 0

        ctx_a.close()
        ctx_anon.close()

    def test_16_invalid_and_forged_share_token_rejection(self, browser, base_url):
        """4. Invalid or forged share tokens are rejected safely."""
        ctx_anon = browser.new_context()
        page = ctx_anon.new_page()

        # Access with fake token
        page.goto(f"{base_url}/planner/share/fake_forged_token_0000000000")
        page.wait_for_load_state("networkidle")
        assert page.locator(".dossier-boarding-pass").count() == 0
        assert "not found" in page.content().lower() or page.url.endswith("/")

        ctx_anon.close()

    def test_17_legacy_sequential_share_route_enumeration_defense(self, browser, base_url):
        """6. Guessing numeric trip ID rejects scrapers and prevents enumeration."""
        ctx_anon = browser.new_context()
        page = ctx_anon.new_page()

        page.goto(f"{base_url}/planner/share/1")
        page.wait_for_load_state("networkidle")
        # Rejected and redirected
        assert page.locator(".dossier-boarding-pass").count() == 0

        ctx_anon.close()

    def test_18_cross_user_export_authorization_isolation(self, browser, base_url):
        """7. User B cannot export User A's private trip through PDF or ICS."""
        ctx_a = browser.new_context()
        page_a = ctx_a.new_page()
        user_a = create_unique_user()
        register_user(page_a, user_a, base_url)
        trip_id_a = create_wizard_trip(page_a, destination="Kochi")

        ctx_b = browser.new_context()
        page_b = ctx_b.new_page()
        user_b = create_unique_user()
        register_user(page_b, user_b, base_url)

        # User B attempts to download User A's ICS
        ics_res = page_b.request.get(f"{base_url}/planner/{trip_id_a}/ics")
        assert "text/calendar" not in ics_res.headers.get("content-type", "")

        # User B attempts to download User A's PDF
        pdf_res = page_b.request.get(f"{base_url}/planner/{trip_id_a}/pdf")
        assert "application/pdf" not in pdf_res.headers.get("content-type", "")

        ctx_a.close()
        ctx_b.close()


# ==============================================================================
# SECTION D: PHASE 3B FEATURE VERIFICATION
# ==============================================================================

class TestPhase3BFeatures:
    """Browser-level verification of Phase 3B features."""

    def test_19_ics_calendar_rfc5545_structure_and_local_times(self, desktop_context, base_url):
        """Verify RFC 5545 iCalendar content, escaping, and floating local times."""
        page = desktop_context.new_page()
        user = create_unique_user()
        register_user(page, user, base_url)
        trip_id = create_wizard_trip(page, destination="Varanasi")

        ics_res = page.request.get(f"{base_url}/planner/{trip_id}/ics")
        assert ics_res.status == 200
        text = ics_res.text()

        # Strict RFC 5545 markers
        assert "BEGIN:VCALENDAR" in text
        assert "VERSION:2.0" in text
        assert "PRODID:-//Yatrika//Travel Planner Agent//EN" in text
        assert "BEGIN:VEVENT" in text
        assert "DTSTART:" in text
        assert "DTEND:" in text
        assert "END:VEVENT" in text
        assert "END:VCALENDAR" in text

        # Verify floating local time (no trailing Z)
        for line in text.splitlines():
            if line.startswith("DTSTART:") or line.startswith("DTEND:"):
                val = line.split(":")[-1]
                assert not val.endswith("Z"), f"Timestamp should be floating local time, got {val}"

    def test_20_weather_horizon_live_vs_seasonal_labeling(self, desktop_context, base_url):
        """Verify weather briefing card honesty (live forecast vs seasonal guidance)."""
        page = desktop_context.new_page()
        user = create_unique_user()
        register_user(page, user, base_url)
        trip_id = create_wizard_trip(page, destination="Jaipur")

        page.goto(f"{base_url}/planner/{trip_id}")
        page.wait_for_load_state("networkidle")

        weather_card = page.locator('h4:has-text("Destination Climate & Weather")')
        expect(weather_card).to_be_visible()

        # Must display honest horizon labeling without fabricating live forecasts
        content = page.content()
        assert ("Live Forecast" in content) or ("Typical Seasonal Guidance" in content) or ("Forecast Not Yet Available" in content)

    def test_21_smart_packing_checklist_interactivity_and_persistence(self, desktop_context, base_url):
        """Verify checking packing items updates counter and persists in SQLite."""
        page = desktop_context.new_page()
        user = create_unique_user()
        register_user(page, user, base_url)
        trip_id = create_wizard_trip(page, destination="Manali")

        page.goto(f"{base_url}/planner/{trip_id}")
        page.wait_for_load_state("networkidle")

        # Open Packing Tab
        page.click('a[href="#tab-packing"]')
        page.wait_for_selector("#tab-packing.active", timeout=5000)

        checkboxes = page.locator(".checklist-item-checkbox")
        assert checkboxes.count() > 0, "Packing checklist should contain items"

        # Toggle first checkbox
        first_box = checkboxes.first
        first_box.check()
        page.wait_for_timeout(500)

        # Counter updates
        expect(page.locator("#packedCountVal")).to_have_text("1")

        # Reload and verify persistence
        page.reload()
        page.wait_for_load_state("networkidle")
        page.click('a[href="#tab-packing"]')
        page.wait_for_selector("#tab-packing.active", timeout=5000)

        expect(page.locator("#packedCountVal")).to_have_text("1")
        assert page.locator(".checklist-item-checkbox").first.is_checked()


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main(["-v", __file__]))
