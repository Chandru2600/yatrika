"""
Feature 8 Tests - Live Recalculation
Verifies:
1. Reordering/moving activities in day planner recalculates budget live (entry fees, transport, daily averages, itemized breakdown).
2. Live recalculation endpoint returns updated totals and breakdown without full wizard re-run or agent pipeline regeneration.
3. Database persistence reflects the updated itinerary and budget JSON.
4. Unauthorized access is blocked.
"""

import unittest
import uuid
import json
import time
from app import create_app
from backend.database.db import init_db
from backend.models.user import create_user
from backend.models.trip import create_trip, update_trip_itinerary, get_trip_by_id


class Feature8RecalculationTestCase(unittest.TestCase):
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
            self.email = f"recalc_{uuid.uuid4().hex[:8]}@yatrika.local"
            self.user_id = create_user("Recalc Tester", self.email, "Pass1234!", role="user")

        with self.client.session_transaction() as sess:
            sess["user_id"] = self.user_id
            sess["user_name"] = "Recalc Tester"
            sess["user_email"] = self.email
            sess["user_role"] = "user"

    def test_live_budget_recalculation_on_planner_edit(self):
        with self.app.app_context():
            trip_data = {
                "destination": "Ooty, Tamil Nadu",
                "source": "Bengaluru",
                "start_date": "2026-12-01",
                "end_date": "2026-12-03",
                "num_days": 3,
                "num_travelers": 2,
                "budget": 20000,
                "travel_style": "leisure",
                "transport": "car"
            }
            trip_id = create_trip(self.user_id, trip_data)
            update_trip_itinerary(
                trip_id,
                itinerary={
                    "trip_summary": "Ooty scenic hill getaway",
                    "selected_attractions": [
                        {"id": 1, "name": "Botanical Gardens", "fee": 50, "dist": 5},
                        {"id": 2, "name": "Ooty Lake", "fee": 100, "dist": 8}
                    ],
                    "day_planner": {
                        "1": {
                            "morning": [{"id": 1, "name": "Botanical Gardens", "fee": 50, "dist": 5}],
                            "afternoon": [{"id": 2, "name": "Ooty Lake", "fee": 100, "dist": 8}],
                            "evening": []
                        },
                        "2": {"morning": [], "afternoon": [], "evening": []},
                        "3": {"morning": [], "afternoon": [], "evening": []}
                    }
                },
                weather={},
                budget={
                    "total_budget": 20000,
                    "daily_average": 6667,
                    "breakdown": {}
                },
                hotels=[]
            )

        # Move activities and add an extra high-fee activity to Day 2
        modified_planner = {
            "1": {
                "morning": [{"id": 1, "name": "Botanical Gardens", "fee": 50, "dist": 5}],
                "afternoon": [],
                "evening": [{"id": 2, "name": "Ooty Lake", "fee": 100, "dist": 8}]
            },
            "2": {
                "morning": [
                    {"id": "custom_tea", "name": "Tea Factory Tour & Tasting", "fee": 450, "dist": 15}
                ],
                "afternoon": [],
                "evening": []
            },
            "3": {
                "morning": [],
                "afternoon": [],
                "evening": []
            }
        }

        start_time = time.time()
        resp = self.client.post(
            f"/planner/{trip_id}/update_planner",
            json={"day_planner": modified_planner}
        )
        elapsed = time.time() - start_time

        # Fast execution without running heavy multi-agent pipeline (< 2.0s)
        self.assertLess(elapsed, 2.0, "Live recalculation must be fast without re-running 4-agent wizard")
        self.assertEqual(resp.status_code, 200)

        data = resp.get_json()
        self.assertTrue(data.get("success"))
        self.assertIn("total_budget", data)
        self.assertIn("daily_average", data)
        self.assertIn("breakdown", data)
        self.assertIn("itinerary_days", data)

        # Check recalculated figures
        # Total entry fees = 50 + 100 + 450 = 600
        self.assertEqual(data["entry_fees"], 600)
        self.assertGreater(data["total_budget"], 0)
        self.assertEqual(data["daily_average"], round(data["total_budget"] / 3))

        # Check breakdown categories
        breakdown = data["breakdown"]
        self.assertIn("activities_tickets", breakdown)
        self.assertEqual(breakdown["activities_tickets"]["amount"], 600)
        self.assertIn("accommodation", breakdown)
        self.assertIn("food_dining", breakdown)
        self.assertIn("transportation", breakdown)

        # Verify DB persistence
        with self.app.app_context():
            saved_trip = get_trip_by_id(trip_id)
            saved_budget = json.loads(saved_trip["budget_json"])
            self.assertEqual(saved_budget["total_budget"], data["total_budget"])
            self.assertEqual(saved_budget["breakdown"]["activities_tickets"]["amount"], 600)

            saved_itinerary = json.loads(saved_trip["itinerary_json"])
            self.assertEqual(len(saved_itinerary["days"]), 3)
            # Day 2 morning should now have the tea factory tour
            day2_morning = saved_itinerary["days"][1]["morning"]
            self.assertIsNotNone(day2_morning)
            self.assertEqual(day2_morning["places"][0]["name"], "Tea Factory Tour & Tasting")

    def test_unauthorized_recalculation_blocked(self):
        # Create trip under user 1
        with self.app.app_context():
            other_email = f"other_{uuid.uuid4().hex[:8]}@yatrika.local"
            other_uid = create_user("Other User", other_email, "Pass1234!", role="user")
            other_trip_id = create_trip(other_uid, {
                "destination": "Goa",
                "source": "Mumbai",
                "start_date": "2026-11-10",
                "end_date": "2026-11-12",
                "num_days": 2,
                "num_travelers": 2,
                "budget": 15000,
                "travel_style": "beach",
                "transport": "flight"
            })

        # Try to modify with current user session (should fail)
        resp = self.client.post(
            f"/planner/{other_trip_id}/update_planner",
            json={"day_planner": {}}
        )
        self.assertEqual(resp.status_code, 404)
        data = resp.get_json()
        self.assertFalse(data.get("success"))
