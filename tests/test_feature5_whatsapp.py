"""
Feature 5 Tests - WhatsApp Share
Verifies:
1. Compact trip summary generated with WhatsApp markdown (*bold*, line breaks).
2. Correct destination, dates, travelers, budget, day-wise highlights with timings, booking links.
3. Intelligent truncation under WhatsApp URL/message limits for multi-day trips.
4. get_whatsapp_share_url returns valid https://wa.me/?text= link.
5. Zero crash resilience against malformed or empty inputs.
6. Integration test on view_trip route ensuring WhatsApp share button renders in HTML.
"""

import unittest
import uuid
import urllib.parse
from app import create_app
from backend.database.db import init_db
from backend.models.user import create_user
from backend.models.trip import create_trip, update_trip_itinerary
from backend.services.share.whatsapp_service import (
    generate_whatsapp_summary,
    get_whatsapp_share_url,
    MAX_WHATSAPP_MESSAGE_CHARS
)


class Feature5WhatsAppTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app("testing")
        cls.app.config["TESTING"] = True
        cls.app.config["WTF_CSRF_ENABLED"] = False
        with cls.app.app_context():
            init_db()

    def test_whatsapp_summary_structure(self):
        trip = {
            "destination": "Goa, India",
            "start_date": "2026-11-10",
            "end_date": "2026-11-13",
            "num_days": 3,
            "num_travelers": 2,
            "budget": 25000
        }
        itinerary = {
            "days": [
                {
                    "day_number": 1,
                    "date": "2026-11-10",
                    "morning": {"attraction": "Calangute Beach", "time": "09:00 - 12:00"},
                    "afternoon": {"attraction": "Aguada Fort", "time": "14:00 - 17:00"},
                    "evening": {"attraction": "Baga Night Market", "time": "18:30 - 21:00"}
                },
                {
                    "day_number": 2,
                    "date": "2026-11-11",
                    "morning": {"attraction": "Dudhsagar Falls", "time": "08:00 - 13:00"},
                    "afternoon": {"attraction": "Spice Plantation Tour", "time": "14:00 - 16:30"},
                    "evening": {"attraction": "Panaji River Cruise", "time": "18:00 - 20:00"}
                }
            ]
        }
        budget = {"total_budget_inr": 25000}
        booking_links = {
            "hotels": [{"name": "MakeMyTrip", "url": "https://www.makemytrip.com/hotels/goa"}],
            "trains": [{"name": "ConfirmTkt", "url": "https://www.confirmtkt.com/trains"}],
            "buses": [{"name": "RedBus", "url": "https://www.redbus.in/bus-tickets"}]
        }

        summary = generate_whatsapp_summary(trip, itinerary, budget, booking_links)

        # Check markdown syntax (*bold*)
        self.assertIn("*YATRIKA TRIP: GOA*", summary)
        self.assertIn("*Dates:*", summary)
        self.assertIn("2026-11-10 → 2026-11-13", summary)
        self.assertIn("*Travelers:* 2", summary)
        self.assertIn("₹25,000", summary)

        # Check day-wise highlights
        self.assertIn("*Day 1*", summary)
        self.assertIn("Calangute Beach", summary)
        self.assertIn("Aguada Fort", summary)
        self.assertIn("[09:00 - 12:00]", summary)

        # Check booking links
        self.assertIn("*QUICK BOOKING:*", summary)
        self.assertIn("makemytrip.com", summary)
        self.assertIn("confirmtkt.com", summary)
        self.assertIn("redbus.in", summary)

        # Verify length within limit
        self.assertLessEqual(len(summary), MAX_WHATSAPP_MESSAGE_CHARS)

    def test_whatsapp_intelligent_truncation(self):
        # 10 days trip with lots of text
        trip = {
            "destination": "Rajasthan Royal Grand Tour, India",
            "start_date": "2026-12-01",
            "end_date": "2026-12-10",
            "num_days": 10,
            "num_travelers": 4,
            "budget": 95000
        }
        days = []
        for i in range(1, 11):
            days.append({
                "day_number": i,
                "date": f"2026-12-{i:02d}",
                "morning": {"attraction": f"Grand Majestic Royal Palace of Rajasthan Historical Fort #{i}", "time": "09:00 - 12:30"},
                "afternoon": {"attraction": f"Ancient Traditional Museum Cultural Exhibition Center #{i}", "time": "14:00 - 17:00"},
                "evening": {"attraction": f"Sunset Desert Dune Safari and Rajasthani Folk Performance #{i}", "time": "18:00 - 21:00"}
            })
        itinerary = {"days": days}
        booking_links = {
            "hotels": [{"url": "https://booking.com/hotels"}],
            "trains": [{"url": "https://confirmtkt.com/trains"}],
            "buses": [{"url": "https://redbus.in/buses"}]
        }

        summary = generate_whatsapp_summary(trip, itinerary, {"total_budget_inr": 95000}, booking_links)
        self.assertLessEqual(len(summary), MAX_WHATSAPP_MESSAGE_CHARS)
        self.assertIn("YATRIKA TRIP", summary)

    def test_get_whatsapp_share_url(self):
        trip = {"destination": "Ooty", "num_days": 2, "start_date": "2026-11-20"}
        url = get_whatsapp_share_url(trip)
        self.assertTrue(url.startswith("https://wa.me/?text="))
        unquoted = urllib.parse.unquote(url)
        self.assertIn("*YATRIKA TRIP: OOTY*", unquoted)

    def test_zero_crash_on_bad_inputs(self):
        # None and empty structures should never throw
        res1 = generate_whatsapp_summary({}, None, None, None)
        self.assertIsInstance(res1, str)
        self.assertIn("YATRIKA TRIP", res1)

        url = get_whatsapp_share_url(None)
        self.assertTrue(url.startswith("https://wa.me/?text="))

    def test_view_trip_renders_whatsapp_button(self):
        with self.app.app_context():
            unique_email = f"wa_{uuid.uuid4().hex[:8]}@yatrika.local"
            uid = create_user("WhatsApp Tester", unique_email, "SecurePass123!", role="user")
            trip_data = {
                "destination": "Coorg, Karnataka",
                "source": "Bengaluru",
                "start_date": "2026-12-05",
                "end_date": "2026-12-07",
                "num_days": 3,
                "num_travelers": 2,
                "budget": 20000,
                "travel_style": "nature",
                "transport": "car"
            }
            trip_id = create_trip(uid, trip_data)
            update_trip_itinerary(
                trip_id,
                itinerary={
                    "days": [
                        {
                            "day_number": 1,
                            "date": "2026-12-05",
                            "morning": {"attraction": "Abbey Falls", "time": "09:00 - 11:30"},
                            "afternoon": {"attraction": "Raja's Seat", "time": "14:00 - 16:30"},
                            "evening": {"attraction": "Madikeri Fort", "time": "17:00 - 18:30"}
                        }
                    ]
                },
                weather={},
                budget={"total_budget_inr": 20000},
                hotels={"base_camp": {"name": "Coorg Estate Resort", "price_per_night": 2800}}
            )

        client = self.app.test_client()
        with client.session_transaction() as sess:
            sess["user_id"] = uid
            sess["user_name"] = "WhatsApp Tester"
            sess["user_email"] = unique_email
            sess["user_role"] = "user"

        resp = client.get(f"/planner/{trip_id}")
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)

        self.assertIn("Share on WhatsApp", html)
        self.assertIn("btnShareWhatsApp", html)
        self.assertIn("https://wa.me/?text=", html)


if __name__ == "__main__":
    unittest.main()
