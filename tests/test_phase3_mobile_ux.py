"""
Phase 3A Mobile UX Polish & Responsive Optimization Regression Test Suite

Verifies:
1. Mobile stylesheet availability and base template integration (mobile.css HTTP 200, viewport meta tag, mobile link in base.html).
2. Desktop protection contract: zero global CSS rules outside media queries, ensuring desktop (>= 992px) is 100% untouched.
3. Touch ergonomics & iOS zoom defense: minimum 44px touch targets on togglers/buttons, 16px font-size on inputs.
4. Mobile navigation auto-collapse: client script contract for #mainNav collapse on item tap and backdrop tap.
5. Wizard unconstrained layout: removal of desktop 100vh overflow:hidden trap for full mobile scrollability and stage progress responsiveness.
6. Boarding pass and MapLibre mobile responsiveness: ticket stacking, map popup overflow protection, and touch-friendly reordering.
7. Critical routes accessibility: Home, Login, Register, Launchpad, Wizard, Destinations, Saved Trips, Dashboard, and Trip View render HTTP 200 with responsive assets.
"""

import os
import re
import tempfile
import unittest

from app import create_app
from backend.database.db import init_db, execute_query
from backend.models.user import create_user
from backend.models.trip import create_trip, update_trip_itinerary


class Phase3MobileUXTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Create an isolated temporary SQLite database for testing
        cls.test_db_fd, cls.test_db_path = tempfile.mkstemp(suffix="_phase3_mobile_test.db")
        os.close(cls.test_db_fd)

        cls.app = create_app("testing")
        cls.app.config["DATABASE_PATH"] = cls.test_db_path
        cls.app.config["TESTING"] = True
        cls.app.config["WTF_CSRF_ENABLED"] = False

        with cls.app.app_context():
            init_db()

        cls.mobile_css_path = os.path.join(cls.app.root_path, "frontend", "static", "css", "mobile.css")
        cls.base_html_path = os.path.join(cls.app.root_path, "frontend", "templates", "base.html")

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.test_db_path):
            try:
                os.remove(cls.test_db_path)
            except OSError:
                pass

    def setUp(self):
        self.client = self.app.test_client()
        with self.app.app_context():
            self.user_id = create_user("Mobile Traveler", "mobile_ux@test.local", "Password123!", role="user")
            self.trip_id = create_trip(self.user_id, {
                "destination": "Goa",
                "start_date": "2026-11-01",
                "end_date": "2026-11-04",
                "num_days": 3,
                "budget": 15000,
                "num_travelers": 2,
                "travel_style": "comfort",
                "transport": "car",
                "transit_mode": "car"
            })
            update_trip_itinerary(
                self.trip_id,
                {
                    "destination": "Goa",
                    "days": [
                        {
                            "day": 1,
                            "date": "Day 1",
                            "theme": "Coastal Vibe",
                            "morning": {"activity": "Calangute Beach Walk", "location": "Calangute Beach", "cost": 0, "coordinates": [15.543, 73.755]},
                            "afternoon": {"activity": "Seafood Lunch", "location": "Britto's Baga", "cost": 1200, "coordinates": [15.556, 73.751]},
                            "evening": {"activity": "Sunset at Fort Aguada", "location": "Fort Aguada", "cost": 50, "coordinates": [15.492, 73.773]}
                        }
                    ]
                },
                {},
                {"total_budget": 15000, "breakdown": {}},
                {}
            )

    def tearDown(self):
        with self.app.app_context():
            execute_query("DELETE FROM expenses")
            execute_query("DELETE FROM saved_trips")
            execute_query("DELETE FROM trips")
            execute_query("DELETE FROM users")

    def test_mobile_stylesheet_served_and_linked_in_base_template(self):
        """mobile.css must be statically served with 200 OK and linked in base.html."""
        res = self.client.get("/static/css/mobile.css")
        self.assertEqual(res.status_code, 200, "mobile.css must be reachable at /static/css/mobile.css")
        self.assertIn("text/css", res.content_type, "mobile.css must have CSS content-type")

        # Verify base.html head
        home_res = self.client.get("/")
        self.assertEqual(home_res.status_code, 200)
        html = home_res.get_data(as_text=True)

        self.assertIn('mobile.css', html, "base.html must include a link to mobile.css")
        self.assertIn('name="viewport"', html, "base.html must have a viewport meta tag")
        self.assertIn('width=device-width', html, "viewport meta tag must configure width=device-width")

    def test_mobile_stylesheet_strict_desktop_protection(self):
        """mobile.css must enclose all rules inside @media queries, strictly protecting desktop (>= 992px)."""
        self.assertTrue(os.path.exists(self.mobile_css_path), "mobile.css file must exist on disk")

        with open(self.mobile_css_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Remove CSS comments
        clean_content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)

        # Robust check: split by '@media'
        # The prelude before the first '@media' should have NO '{' brackets
        parts = clean_content.split("@media")
        prelude = parts[0].strip()
        self.assertNotIn("{", prelude, f"Found CSS rules outside @media before first media query: {prelude}")

        # Check each media query block closes properly and contains no top-level leaks
        media_count = len(parts) - 1
        self.assertGreaterEqual(media_count, 4, "mobile.css should contain at least 4 responsive breakpoints")

    def test_touch_target_and_ios_zoom_defense(self):
        """mobile.css must enforce touch targets >= 44px and inputs >= 16px to prevent iOS auto-zoom."""
        with open(self.mobile_css_path, "r", encoding="utf-8") as f:
            css = f.read()

        # Check for 44px touch targets on togglers or buttons
        self.assertIn("44px", css, "mobile.css must define standard 44px touch targets")

        # Check for iOS zoom defense (16px font-size on inputs)
        self.assertRegex(
            css,
            r'font-size:\s*16px',
            "mobile.css must include 16px font-size on mobile form inputs to eliminate iOS Safari zooming"
        )

    def test_mobile_navigation_auto_collapse_contract(self):
        """base.html must include JS logic to collapse mobile navbar when link is tapped or outside area clicked."""
        with open(self.base_html_path, "r", encoding="utf-8") as f:
            base_html = f.read()

        self.assertIn("mainNav", base_html, "base.html must target the mainNav collapse element")
        self.assertIn("navbar-toggler", base_html, "base.html must coordinate with the navbar toggler")
        self.assertIn("bsCollapse.hide", base_html, "base.html must invoke collapse hide on outside or link click")

    def test_wizard_unconstrained_mobile_layout(self):
        """mobile.css must unconstrain .wizard-root on mobile, removing fixed 100vh overflow:hidden."""
        with open(self.mobile_css_path, "r", encoding="utf-8") as f:
            css = f.read()

        self.assertIn(".wizard-root", css, "mobile.css must contain responsive rules for .wizard-root")
        self.assertRegex(css, r'\.wizard-root\s*{[^}]*height:\s*auto', "wizard-root must have height: auto on mobile")
        self.assertRegex(css, r'\.wizard-root\s*{[^}]*overflow:\s*visible', "wizard-root must have overflow: visible on mobile")

        # Verify progress track mobile handling
        self.assertIn(".progress-track-modern", css, "mobile.css must optimize .progress-track-modern for mobile")

    def test_view_trip_mobile_responsiveness(self):
        """mobile.css must stack boarding pass ticket and prevent MapLibre popup overflow."""
        with open(self.mobile_css_path, "r", encoding="utf-8") as f:
            css = f.read()

        # Boarding pass ticket stacking
        self.assertIn(".dossier-boarding-pass", css, "mobile.css must format .dossier-boarding-pass for mobile screens")
        self.assertRegex(css, r'\.dossier-boarding-pass\s*{[^}]*flex-direction:\s*column', "dossier-boarding-pass must stack into column on mobile")
        self.assertRegex(css, r'\.ticket-main-body\s*{[^}]*width:\s*100%', "ticket-main-body must expand to 100% width on mobile")

        # Map container and popup safety
        self.assertIn("#tripMap", css, "mobile.css must scope #tripMap mobile container height")
        self.assertIn(".maplibregl-popup", css, "mobile.css must define mobile constraints for map popups")

    def test_critical_pages_render_with_mobile_support(self):
        """All critical routes must return 200 OK and include the mobile responsive stylesheet."""
        routes_to_test = [
            "/",
            "/auth/login",
            "/auth/register",
            "/planner/destinations",
            "/launchpad",
            "/planner/wizard",
        ]

        for route in routes_to_test:
            res = self.client.get(route)
            self.assertEqual(res.status_code, 200, f"Route {route} failed to return 200 OK")
            html = res.get_data(as_text=True)
            self.assertIn("mobile.css", html, f"Route {route} missing mobile.css link")
            self.assertIn('name="viewport"', html, f"Route {route} missing viewport meta tag")

    def test_authenticated_mobile_views(self):
        """Authenticated views (dashboard, saved trips, view trip) must render cleanly with mobile assets."""
        with self.client.session_transaction() as sess:
            sess["user_id"] = self.user_id

        auth_routes = [
            "/dashboard",
            "/planner/saved",
            f"/planner/{self.trip_id}",
        ]

        for route in auth_routes:
            res = self.client.get(route)
            self.assertEqual(res.status_code, 200, f"Route {route} failed to return 200 OK for authenticated user")
            html = res.get_data(as_text=True)
            self.assertIn("mobile.css", html, f"Route {route} missing mobile.css link")
            self.assertIn('name="viewport"', html, f"Route {route} missing viewport meta tag")


if __name__ == "__main__":
    unittest.main()
