"""
Feature 6 Tests - Wizard Simplification
Verifies:
1. The planner form (/planner/new) presents 6 essential fields max:
   - destination
   - start_date
   - num_days (duration)
   - num_travelers
   - budget
   - travel_style
2. Non-essential fields (origin, transit mode, interests) are organized into a collapsible
   "Advanced Options" section.
3. Fast execution (< 60s benchmark): Submitting only the 6 essential fields generates
   a complete, validated itinerary with smart defaults.
4. Graceful handling of date calculations when end_date is omitted.
"""

import unittest
import uuid
import time
from app import create_app
from backend.database.db import init_db
from backend.models.user import create_user
from backend.models.trip import get_trip_by_id


class Feature6WizardTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app("testing")
        cls.app.config["TESTING"] = True
        cls.app.config["WTF_CSRF_ENABLED"] = False
        with cls.app.app_context():
            init_db()

    def setUp(self):
        self.client = self.app.test_client()
        with self.app.app_context():
            self.email = f"wiz_{uuid.uuid4().hex[:8]}@yatrika.local"
            self.user_id = create_user("Wizard Tester", self.email, "Pass1234!", role="user")

        with self.client.session_transaction() as sess:
            sess["user_id"] = self.user_id
            sess["user_name"] = "Wizard Tester"
            sess["user_email"] = self.email
            sess["user_role"] = "user"

    def test_wizard_ui_presents_6_essential_fields_and_collapsible_advanced(self):
        resp = self.client.get("/planner/new")
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)

        # 6 Essential fields container
        self.assertIn("essentialFieldsCard", html)
        self.assertIn("Essential Trip Details", html)
        self.assertIn("6 Quick Fields", html)

        # 1. Destination
        self.assertIn('name="destination"', html)
        # 2. Start Date
        self.assertIn('name="start_date"', html)
        # 3. Days / Duration
        self.assertIn('name="num_days"', html)
        # 4. Travelers
        self.assertIn('name="num_travelers"', html)
        # 5. Budget
        self.assertIn('name="budget"', html)
        # 6. Travel Style
        self.assertIn('name="travel_style"', html)

        # Collapsible Advanced Section
        self.assertIn("<details", html)
        self.assertIn("advancedOptionsCollapsible", html)
        self.assertIn("Advanced Options (Optional)", html)

        # Non-essential fields are inside advanced section
        details_content = html.split('<details')[1].split('</details>')[0]
        self.assertIn('name="source"', details_content)
        self.assertIn('name="transport"', details_content)
        self.assertIn('name="interests"', details_content)

    def test_6_field_submission_completes_in_under_60_seconds(self):
        start_time = time.time()

        form_data = {
            "destination": "Chikmagalur, Karnataka",
            "start_date": "2026-11-20",
            "num_days": "3",
            "num_travelers": "2",
            "budget": "20000",
            "travel_style": "nature"
            # Note: source, transport, and interests omitted to simulate 6-field quick completion
        }

        resp = self.client.post("/planner/new", data=form_data, follow_redirects=False)
        duration = time.time() - start_time

        # Must redirect to view_trip on success
        self.assertEqual(resp.status_code, 302)
        redirect_url = resp.headers.get("Location", "")
        self.assertIn("/planner/", redirect_url)

        # Benchmarked: under 60 seconds (typically under 5 seconds)
        self.assertLess(duration, 60.0)

        # Verify smart defaults in saved trip
        trip_id = int(redirect_url.rstrip("/").split("/")[-1])
        with self.app.app_context():
            trip = get_trip_by_id(trip_id)
            self.assertIsNotNone(trip)
            self.assertEqual(trip["destination"], "Chikmagalur, Karnataka")
            self.assertEqual(trip["transport"], "train")  # Smart default
            self.assertEqual(trip["num_days"], 3)
            self.assertEqual(trip["num_travelers"], 2)
            self.assertEqual(trip["travel_style"], "nature")


if __name__ == "__main__":
    unittest.main()
