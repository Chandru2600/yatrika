"""
Feature 9 Tests - Hide the Machinery
Verifies:
1. All user-facing routes (home, dashboard, destinations, new trip wizard, trip view)
   are scrubbed of internal engineering jargon:
   - "Agent 1", "Agent 2", "Agent 3", "Agent 4", "4-Agent", "multi-agent pipeline",
     "orienteering", "IBM Granite", "RF Regressor", "Random Forest ML".
2. Plain language traveler-friendly terms are displayed instead:
   - "Smart Stay Curation", "Transit Optimization", "Smart Cost Estimator",
     "Smart Cost Verified", "Cost Verified", etc.
"""

import unittest
import uuid
from app import create_app
from backend.database.db import init_db
from backend.models.user import create_user
from backend.models.trip import create_trip, update_trip_itinerary


class Feature9CleanUITestCase(unittest.TestCase):
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
            self.email = f"clean_ui_{uuid.uuid4().hex[:8]}@yatrika.local"
            self.user_id = create_user("Clean UI Tester", self.email, "Pass1234!", role="user")

        with self.client.session_transaction() as sess:
            sess["user_id"] = self.user_id
            sess["user_name"] = "Clean UI Tester"
            sess["user_email"] = self.email
            sess["user_role"] = "user"

        with self.app.app_context():
            self.trip_id = create_trip(self.user_id, {
                "destination": "Chikmagalur, Karnataka",
                "source": "Bengaluru",
                "start_date": "2026-11-20",
                "end_date": "2026-11-22",
                "num_days": 2,
                "num_travelers": 2,
                "budget": 18000,
                "travel_style": "nature",
                "transport": "car"
            })
            update_trip_itinerary(
                self.trip_id,
                itinerary={
                    "trip_summary": "Chikmagalur coffee estate getaway",
                    "days": [
                        {
                            "day": 1,
                            "date": "Day 1",
                            "theme": "Coffee Plantations",
                            "morning": {"activity": "Coffee Tour", "place": "Estate", "duration": "2h", "entry_fee": "Free", "places": []},
                            "afternoon": {"activity": "Mullayanagiri Peak", "place": "Peak", "duration": "3h", "entry_fee": "₹20", "places": []},
                            "evening": {"activity": "Sunset Point", "place": "Viewpoint", "duration": "1.5h", "entry_fee": "Free", "places": []}
                        }
                    ],
                    "cultural_etiquette": ["Respect quiet hours in estate homestays"]
                },
                weather={},
                budget={
                    "total_budget": 18000,
                    "daily_average": 9000,
                    "breakdown": {}
                },
                hotels={
                    "base_camp": {"name": "Java Rain Resort", "address": "Chikmagalur", "price_per_night": 4500, "rating": 4.6},
                    "budget_hotels": [{"name": "Planters Court", "address": "Chikmagalur", "price_per_night": 2200, "rating": 4.2}]
                }
            )

    def test_home_page_clean_of_internal_jargon(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)

        banned_terms = [
            "Agent 1", "Agent 2", "Agent 3", "Agent 4",
            "4-Agent", "multi-agent pipeline",
            "orienteering", "RF Regressor", "Random Forest ML"
        ]
        for term in banned_terms:
            self.assertNotIn(term, html, f"Banned jargon '{term}' found on home page")

        # Friendly replacements must exist
        self.assertIn("Smart Stay Curation", html)
        self.assertIn("Transit Optimization", html)
        self.assertIn("Smart Cost Estimator", html)

    def test_destinations_page_clean_of_internal_jargon(self):
        resp = self.client.get("/planner/destinations")
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)

        banned_terms = [
            "4-Agent Cooperative", "multi-agent pipeline",
            "Agent 1", "Agent 2", "Agent 3", "IBM Granite models"
        ]
        for term in banned_terms:
            self.assertNotIn(term, html, f"Banned jargon '{term}' found on destinations page")

        self.assertIn("Smart Stay Curation", html)
        self.assertIn("Transit Optimization", html)
        self.assertIn("Smart Cost Estimator", html)

    def test_dashboard_clean_of_internal_jargon(self):
        resp = self.client.get("/dashboard")
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)

        banned_terms = [
            "Granite AI Travel Concierge",
            "⚡ Granite Express Auto-Pilot",
            "IBM Granite AI"
        ]
        for term in banned_terms:
            self.assertNotIn(term, html, f"Banned jargon '{term}' found on dashboard")

        self.assertIn("Yatrika AI Travel Concierge", html)
        self.assertIn("⚡ Express Auto-Pilot", html)

    def test_trip_view_clean_of_internal_jargon(self):
        resp = self.client.get(f"/planner/{self.trip_id}")
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)

        banned_terms = [
            "Random Forest ML",
            "ML Verified",
            "Agent 1", "Agent 2", "Agent 3", "Agent 4",
            "orienteering"
        ]
        for term in banned_terms:
            self.assertNotIn(term, html, f"Banned jargon '{term}' found on trip view")

        self.assertIn("Smart Cost Verified", html)
        self.assertIn("Cost Verified", html)
