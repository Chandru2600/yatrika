"""
Feature 1 Tests - Actionable Booking Links
Verifies:
1. build_booking_links() returns structured deep links for Hotels, Trains, and Buses.
2. Hotel links contain destination, checkin, checkout, and guests.
3. Train links contain source, destination, and date (ConfirmTkt & IRCTC).
4. Bus links contain source, destination, and date (RedBus).
5. Zero crash resilience against empty, malformed, or missing inputs.
6. Integration test on view_trip route ensuring booking buttons are rendered in HTML.
"""

import unittest
from datetime import date, timedelta
from urllib.parse import unquote

from app import create_app
from backend.services.booking.booking_service import build_booking_links
from backend.database.db import init_db
from backend.models.user import create_user
from backend.models.trip import create_trip, update_trip_itinerary


class Feature1BookingTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app("testing")
        cls.app.config["TESTING"] = True
        cls.app.config["WTF_CSRF_ENABLED"] = False
        with cls.app.app_context():
            init_db()

    def test_build_booking_links_structure(self):
        trip = {
            "destination": "Goa, India",
            "source": "Mumbai, Maharashtra",
            "start_date": "2026-11-10",
            "end_date": "2026-11-14",
            "num_days": 4,
            "num_travelers": 2
        }
        res = build_booking_links(trip)
        self.assertIn("hotels", res)
        self.assertIn("trains", res)
        self.assertIn("buses", res)
        self.assertIn("summary", res)

        # Check Hotel links
        hotels = res["hotels"]
        providers = [h["provider"] for h in hotels]
        self.assertIn("MakeMyTrip", providers)
        self.assertIn("Goibibo", providers)
        self.assertIn("Booking.com", providers)

        # Verify Booking.com deep link parameters
        bcom = next(h for h in hotels if h["provider"] == "Booking.com")
        self.assertIn("ss=Goa", bcom["url"])
        self.assertIn("checkin=2026-11-10", bcom["url"])
        self.assertIn("checkout=2026-11-14", bcom["url"])
        self.assertIn("group_adults=2", bcom["url"])

        # Check Train links
        trains = res["trains"]
        t_providers = [t["provider"] for t in trains]
        self.assertIn("ConfirmTkt", t_providers)
        self.assertIn("IRCTC", t_providers)

        ctkt = next(t for t in trains if t["provider"] == "ConfirmTkt")
        self.assertIn("/from/Mumbai/to/Goa/", ctkt["url"])
        self.assertIn("10-11-2026", ctkt["url"])

        irctc = next(t for t in trains if t["provider"] == "IRCTC")
        self.assertIn("srcStation=Mumbai", irctc["url"])
        self.assertIn("destStation=Goa", irctc["url"])
        self.assertIn("journeyDate=10112026", irctc["url"])

        # Check Bus links
        buses = res["buses"]
        rb = next(b for b in buses if b["provider"] == "RedBus")
        self.assertIn("mumbai-to-goa", rb["url"])
        self.assertIn("10-Nov-2026", rb["url"])

    def test_build_booking_links_zero_crash_on_bad_inputs(self):
        # Empty dict
        res_empty = build_booking_links({})
        self.assertIsInstance(res_empty, dict)
        self.assertTrue(len(res_empty.get("hotels", [])) > 0)
        self.assertTrue(len(res_empty.get("trains", [])) > 0)
        self.assertTrue(len(res_empty.get("buses", [])) > 0)

        # None input
        res_none = build_booking_links(None)
        self.assertIsInstance(res_none, dict)
        self.assertTrue(len(res_none.get("hotels", [])) > 0)

        # Malformed dates and negative numbers
        res_bad = build_booking_links({
            "destination": "",
            "source": "",
            "start_date": "not-a-valid-date",
            "end_date": "also-not-valid",
            "num_days": -5,
            "num_travelers": -1
        })
        self.assertIsInstance(res_bad, dict)
        self.assertTrue(len(res_bad["hotels"]) > 0)

    def test_view_trip_renders_booking_buttons(self):
        import uuid
        with self.app.app_context():
            unique_email = f"booking_{uuid.uuid4().hex[:8]}@yatrika.local"
            uid = create_user("Booking Tester", unique_email, "Pass1234!", role="user")
            trip_data = {
                "destination": "Jaipur, Rajasthan",
                "source": "Delhi",
                "start_date": "2026-12-01",
                "end_date": "2026-12-04",
                "num_days": 3,
                "num_travelers": 2,
                "budget": 30000,
                "travel_style": "cultural",
                "transport": "train"
            }
            trip_id = create_trip(uid, trip_data)
            update_trip_itinerary(
                trip_id,
                itinerary={"days": [{"day": 1, "title": "Day 1 Loop"}]},
                weather={},
                budget={"total_budget": 30000},
                hotels={"base_camp": {"name": "Jaipur Haveli", "price_per_night": 2200}}
            )

        client = self.app.test_client()
        with client.session_transaction() as sess:
            sess["user_id"] = uid
            sess["user_name"] = "Booking Tester"
            sess["user_email"] = "booking_test@yatrika.local"
            sess["user_role"] = "user"

        resp = client.get(f"/planner/{trip_id}")
        self.assertEqual(resp.status_code, 200)
        html = resp.data.decode("utf-8")

        # Verify booking button and provider deep links exist in rendered HTML
        self.assertIn("Book Stays &amp; Transit", html)
        self.assertIn("MakeMyTrip", html)
        self.assertIn("Booking.com", html)
        self.assertIn("ConfirmTkt", html)
        self.assertIn("RedBus", html)
        self.assertIn("makemytrip.com/hotels", html)
        self.assertIn("booking.com/searchresults.html", html)
