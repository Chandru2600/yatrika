"""
Feature 7 Tests - Layout: Practical First
Verifies:
1. Reordered itinerary day view:
   - Timings, costs, addresses, and booking buttons are rendered at the top (practicalEssentialsCard + daily-loop-cards).
   - Cultural narrative, etiquette notes, and useful phrases are rendered below (culturalInsightsSection).
2. Zero content deletion:
   - Booking action buttons, slot timings/costs/addresses, and Granite narrative/cultural wisdom all exist.
3. Order assertion:
   - index("practicalEssentialsCard") < index("culturalInsightsSection")
"""

import unittest
import uuid
from app import create_app
from backend.database.db import init_db
from backend.models.user import create_user
from backend.models.trip import create_trip, update_trip_itinerary


class Feature7LayoutTestCase(unittest.TestCase):
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
            self.email = f"layout_{uuid.uuid4().hex[:8]}@yatrika.local"
            self.user_id = create_user("Layout Tester", self.email, "Pass1234!", role="user")

        with self.client.session_transaction() as sess:
            sess["user_id"] = self.user_id
            sess["user_name"] = "Layout Tester"
            sess["user_email"] = self.email
            sess["user_role"] = "user"

    def test_practical_first_layout_order(self):
        with self.app.app_context():
            trip_data = {
                "destination": "Coorg, Karnataka",
                "source": "Bengaluru",
                "start_date": "2026-11-25",
                "end_date": "2026-11-27",
                "num_days": 3,
                "num_travelers": 2,
                "budget": 24000,
                "travel_style": "nature",
                "transport": "train"
            }
            trip_id = create_trip(self.user_id, trip_data)
            update_trip_itinerary(
                trip_id,
                itinerary={
                    "trip_summary": "Coorg is a tranquil hill station enveloped in coffee plantations, mist, and Kodava hospitality.",
                    "cultural_etiquette": ["Remove shoes before entering sacred shrines", "Respect private coffee estates"],
                    "useful_phrases": [
                        {"phrase": "Thank you", "local": "Dhanyavada", "pronunciation": "dhan-ya-vaad-a"},
                        {"phrase": "How much?", "local": "Eshtu?", "pronunciation": "esh-tu"}
                    ],
                    "days": [
                        {
                            "day_number": 1,
                            "date": "2026-11-25",
                            "morning": {
                                "name": "Abbey Waterfalls",
                                "time": "09:00 - 11:30",
                                "cost": 50,
                                "dur": "2.5h",
                                "proximity": "Near Madikeri Town"
                            },
                            "afternoon": {
                                "name": "Raja's Seat Viewpoint",
                                "time": "14:00 - 16:30",
                                "cost": 30,
                                "dur": "2.5h",
                                "proximity": "Central Madikeri"
                            },
                            "evening": {
                                "name": "Madikeri Heritage Fort",
                                "time": "17:00 - 18:30",
                                "cost": 0,
                                "dur": "1.5h",
                                "proximity": "Stuart Hill"
                            }
                        }
                    ]
                },
                weather={},
                budget={"total_budget_inr": 24000},
                hotels={"base_camp": {"name": "Heritage Kodagu Estate Resort", "address": "Madikeri Hill Road", "price_per_night": 2800}}
            )

        resp = self.client.get(f"/planner/{trip_id}")
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)

        # 1. Verify practical elements are present
        self.assertIn("practicalEssentialsCard", html)
        self.assertIn("Heritage Kodagu Estate Resort", html)
        self.assertIn("Madikeri Hill Road", html)
        self.assertIn("Direct Provider Booking", html)

        # 2. Verify daily loop practical timings, costs, and addresses
        self.assertIn("09:00 - 11:30", html)
        self.assertIn("₹50", html)
        self.assertIn("Near Madikeri Town", html)

        # 3. Verify cultural elements are present
        self.assertIn("culturalInsightsSection", html)
        self.assertIn("Coorg is a tranquil hill station", html)
        self.assertIn("Remove shoes before entering sacred shrines", html)
        self.assertIn("Dhanyavada", html)

        # 4. CRITICAL: Verify order (practical first, narrative below)
        idx_practical = html.index("practicalEssentialsCard")
        idx_daily_loops = html.index("Day-by-Day Itinerary Loops")
        idx_cultural = html.index("culturalInsightsSection")

        self.assertLess(idx_practical, idx_daily_loops, "Practical booking card must precede daily loops")
        self.assertLess(idx_daily_loops, idx_cultural, "Daily practical loops must precede narrative/cultural insights")


if __name__ == "__main__":
    unittest.main()
