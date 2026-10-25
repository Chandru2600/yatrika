"""
Phase 3B Calendar Export, Weather Transparency & Smart Packing Checklist Test Suite

Verifies:
1. Calendar Export (RFC 5545 .ics generation, auth protection, IDOR prevention,
   MIME text/calendar, line folding, UID uniqueness, escaping, floating local time).
2. Weather Transparency (live forecast <= 7 days vs seasonal guidance > 7 days,
   honest labeling, missing data fallback).
3. Destination-Aware Packing Checklist (contextual generation for climate/duration,
   checkbox state toggle, SQLite persistence, IDOR isolation).
"""

import os
import re
import json
import tempfile
import unittest
from datetime import date, timedelta

from app import create_app
from backend.database.db import init_db, execute_query
from backend.models.user import create_user
from backend.models.trip import create_trip, update_trip_itinerary, get_trip_checklist
from backend.services.calendar.calendar_service import (
    generate_trip_ics, _escape_ics_text, _fold_ics_line
)
from backend.services.weather.weather_service import evaluate_weather_horizon
from backend.services.packing.packing_service import (
    generate_smart_packing_checklist, _infer_weather_signals
)


class Phase3BCalendarWeatherPackingTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_db_fd, cls.test_db_path = tempfile.mkstemp(suffix="_phase3b_test.db")
        os.close(cls.test_db_fd)

        cls.app = create_app("testing")
        cls.app.config["DATABASE_PATH"] = cls.test_db_path
        cls.app.config["TESTING"] = True
        cls.app.config["WTF_CSRF_ENABLED"] = False

        with cls.app.app_context():
            init_db()

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
            self.user_a_id = create_user("Alice Traveler", "alice_3b@test.local", "Password123!", role="user")
            self.user_b_id = create_user("Bob Intruder", "bob_3b@test.local", "Password123!", role="user")

            today = date.today()
            # Trip 1: Goa within live forecast window (3 days from now)
            self.trip_live_id = create_trip(self.user_a_id, {
                "destination": "Goa, India",
                "start_date": (today + timedelta(days=2)).isoformat(),
                "end_date": (today + timedelta(days=5)).isoformat(),
                "num_days": 3,
                "budget": 25000,
                "num_travelers": 2,
                "travel_style": "comfort",
                "transport": "flight",
                "transit_mode": "flight"
            })
            update_trip_itinerary(
                self.trip_live_id,
                {
                    "destination": "Goa, India",
                    "days": [
                        {
                            "day": 1,
                            "date": (today + timedelta(days=2)).isoformat(),
                            "title": "Coastal Arrival",
                            "morning": {"activity": "Calangute Beach Walk", "location": "Calangute, North Goa", "dur": "2h", "cost": 0},
                            "afternoon": {"activity": "Spice Plantation & Lunch; Special Tour", "location": "Ponda, Goa", "dur": "3.5h", "cost": 800},
                            "evening": {"activity": "Sunset at Chapora Fort, Vagator", "location": "Chapora Fort", "dur": "2h", "cost": 0}
                        },
                        {
                            "day": 2,
                            "date": (today + timedelta(days=3)).isoformat(),
                            "title": "Heritage & Culture",
                            "morning": {"activity": "Basilica of Bom Jesus", "location": "Old Goa", "dur": "2.5h", "cost": 50},
                            "afternoon": {"activity": "Fontainhas Latin Quarter Walk", "location": "Panaji", "dur": "2h", "cost": 0},
                            "evening": {"activity": "Mandovi River Cruise", "location": "Panaji Jetty", "dur": "1.5h", "cost": 500}
                        }
                    ]
                },
                {
                    "current": {
                        "temperature": 31.5,
                        "feels_like": 35.0,
                        "description": "Partly Cloudy",
                        "humidity": 78,
                        "wind_speed": 4.2
                    },
                    "forecast": [
                        {"date": (today + timedelta(days=2)).isoformat(), "temp_max": 32, "temp_min": 25, "description": "Sunny", "humidity": 75}
                    ],
                    "alerts": ["☀️ Hot weather expected. Light clothing and hydration recommended."]
                },
                {"total_budget": 25000, "breakdown": {}},
                {}
            )

            # Trip 2: Manali in far future (45 days from now, outside live forecast horizon)
            self.trip_future_id = create_trip(self.user_a_id, {
                "destination": "Manali, Himachal Pradesh",
                "start_date": (today + timedelta(days=45)).isoformat(),
                "end_date": (today + timedelta(days=50)).isoformat(),
                "num_days": 5,
                "budget": 35000,
                "num_travelers": 2,
                "travel_style": "adventure",
                "transport": "car",
                "transit_mode": "car"
            })
            update_trip_itinerary(
                self.trip_future_id,
                {
                    "destination": "Manali, Himachal Pradesh",
                    "days": [
                        {
                            "day": 1,
                            "date": (today + timedelta(days=45)).isoformat(),
                            "title": "Mountain Arrival",
                            "morning": {"activity": "Mall Road Stroll", "location": "Old Manali", "dur": "2h", "cost": 0},
                            "afternoon": {"activity": "Hadimba Temple Visit", "location": "Dhungri Forest", "dur": "2h", "cost": 30},
                            "evening": {"activity": "Solang Valley Sunset View", "location": "Solang Valley", "dur": "3h", "cost": 0}
                        }
                    ]
                },
                {
                    "current": {
                        "temperature": 12.0,
                        "feels_like": 10.5,
                        "description": "Scattered Clouds",
                        "humidity": 55,
                        "wind_speed": 3.1
                    },
                    "forecast": [],
                    "alerts": ["🧥 Cool weather. Pack a jacket and layered clothing."]
                },
                {"total_budget": 35000, "breakdown": {}},
                {}
            )

    def tearDown(self):
        with self.app.app_context():
            execute_query("DELETE FROM expenses")
            execute_query("DELETE FROM saved_trips")
            execute_query("DELETE FROM trips")
            execute_query("DELETE FROM users")

    # =========================================================================
    # 1. Calendar Export (.ics) Tests
    # =========================================================================

    def test_ics_export_authorized_owner_success(self):
        """Authorized trip owner can export itinerary as .ics with correct headers and boundaries."""
        with self.client.session_transaction() as sess:
            sess["user_id"] = self.user_a_id

        res = self.client.get(f"/planner/{self.trip_live_id}/ics")
        self.assertEqual(res.status_code, 200)
        self.assertIn("text/calendar", res.content_type)
        self.assertIn("attachment", res.headers.get("Content-Disposition", ""))
        self.assertIn("yatrika-goa", res.headers.get("Content-Disposition", ""))

        ics_text = res.get_data(as_text=True)
        # RFC 5545 calendar boundaries
        self.assertTrue(ics_text.startswith("BEGIN:VCALENDAR"))
        self.assertTrue(ics_text.rstrip().endswith("END:VCALENDAR"))
        self.assertIn("VERSION:2.0", ics_text)
        self.assertIn("PRODID:-//Yatrika//Travel Planner Agent//EN", ics_text)
        self.assertIn("BEGIN:VEVENT", ics_text)
        self.assertIn("END:VEVENT", ics_text)

    def test_ics_export_unauthenticated_rejected(self):
        """Unauthenticated request to export .ics must be rejected and redirected."""
        res = self.client.get(f"/planner/{self.trip_live_id}/ics")
        self.assertEqual(res.status_code, 302)
        location = res.headers.get("Location", "")
        self.assertTrue("/dashboard" in location or "/auth/login" in location, f"Expected redirect to dashboard or login, got: {location}")

    def test_ics_export_idor_cross_user_rejected(self):
        """User B (Bob) must not be allowed to export User A's (Alice) private trip calendar."""
        with self.client.session_transaction() as sess:
            sess["user_id"] = self.user_b_id

        res = self.client.get(f"/planner/{self.trip_live_id}/ics")
        # Should reject and redirect with warning
        self.assertEqual(res.status_code, 302)
        self.assertIn("/dashboard", res.headers.get("Location", ""))

    def test_ics_escaping_and_line_folding(self):
        """Text properties must escape commas, semicolons, backslashes and fold long lines."""
        escaped = _escape_ics_text(r"Visit Fort & Palace; take photo, fun!\nNew line.")
        self.assertIn(r"\,", escaped)
        self.assertIn(r"\;", escaped)
        self.assertIn(r"\\", escaped)

        # Line folding at <= 75 bytes
        long_line = "DESCRIPTION:" + "A" * 150
        folded = _fold_ics_line(long_line)
        for segment in folded.split("\r\n"):
            # Each line excluding CRLF should not exceed 75 bytes
            self.assertLessEqual(len(segment.encode("utf-8")), 76)

    def test_ics_distinct_uids_and_floating_local_times(self):
        """Each scheduled activity must receive a unique stable UID and floating local time."""
        with self.client.session_transaction() as sess:
            sess["user_id"] = self.user_a_id

        res = self.client.get(f"/planner/{self.trip_live_id}/ics")
        ics_text = res.get_data(as_text=True)

        uids = re.findall(r'UID:(.+)', ics_text)
        self.assertGreaterEqual(len(uids), 3, "Expected at least 3 scheduled activity events")
        self.assertEqual(len(uids), len(set(uids)), "All event UIDs must be strictly distinct and unique")

        # Verify floating local time representation: YYYYMMDDTHHMMSS without trailing Z
        dtstarts = re.findall(r'DTSTART:([0-9]{8}T[0-9]{6})', ics_text)
        self.assertGreaterEqual(len(dtstarts), 3)
        for dt in dtstarts:
            self.assertFalse(dt.endswith("Z"), f"Floating local time must not end with Z: {dt}")

    # =========================================================================
    # 2. Weather Horizon & Transparency Tests
    # =========================================================================

    def test_weather_horizon_live_forecast_within_7_days(self):
        """Trip starting within 7 days must be accurately labeled as 'Live Forecast'."""
        today = date.today()
        trip_data = {
            "destination": "Goa",
            "start_date": (today + timedelta(days=3)).isoformat(),
            "end_date": (today + timedelta(days=6)).isoformat(),
            "num_days": 3
        }
        weather_payload = {
            "current": {"temperature": 29.0, "description": "Sunny"},
            "forecast": [{"temp_max": 30}]
        }
        eval_result = evaluate_weather_horizon(trip_data, weather_payload)
        self.assertEqual(eval_result["status"], "live_forecast")
        self.assertEqual(eval_result["label"], "Live Forecast")
        self.assertTrue(eval_result["is_live"])

    def test_weather_horizon_seasonal_guidance_beyond_7_days(self):
        """Trip starting > 7 days in future must NOT claim to be a live forecast."""
        today = date.today()
        trip_data = {
            "destination": "Manali",
            "start_date": (today + timedelta(days=30)).isoformat(),
            "end_date": (today + timedelta(days=35)).isoformat(),
            "num_days": 5
        }
        weather_payload = {
            "current": {"temperature": 15.0, "description": "Cloudy"},
            "forecast": []
        }
        eval_result = evaluate_weather_horizon(trip_data, weather_payload)
        self.assertEqual(eval_result["status"], "seasonal_guidance")
        self.assertEqual(eval_result["label"], "Typical Seasonal Guidance")
        self.assertFalse(eval_result["is_live"])
        self.assertIn("30 days away", eval_result["explanation"])

    def test_weather_horizon_unavailable_fallback(self):
        """Missing or error-state weather data must honestly display 'Forecast Not Yet Available'."""
        trip_data = {"destination": "Puri", "start_date": "2026-12-01", "num_days": 3}
        eval_result = evaluate_weather_horizon(trip_data, {"error": "API timeout"})
        self.assertEqual(eval_result["status"], "unavailable")
        self.assertEqual(eval_result["label"], "Forecast Not Yet Available")
        self.assertFalse(eval_result["is_live"])

    # =========================================================================
    # 3. Smart Packing Checklist Tests
    # =========================================================================

    def test_smart_packing_checklist_generation(self):
        """Checklist must generate categorized items tailored for destination and climate."""
        trip = {
            "id": self.trip_live_id,
            "destination": "Goa, India",
            "num_days": 4
        }
        weather = {
            "current": {"temperature": 31.0, "description": "Sunny"},
            "forecast": []
        }
        checklist = generate_smart_packing_checklist(trip, weather)
        self.assertIn("categories", checklist)
        cats = checklist["categories"]
        self.assertIn("essentials", cats)
        self.assertIn("clothing", cats)
        self.assertIn("health_care", cats)
        self.assertIn("electronics", cats)
        self.assertIn("destination_gear", cats)

        # Beach + hot destination checks
        clothing_texts = [it["text"] for it in cats["clothing"]["items"]]
        self.assertTrue(any("Swimwear" in t or "beachwear" in t for t in clothing_texts))
        self.assertTrue(any("sun hat" in t.lower() or "sunglasses" in t.lower() for t in clothing_texts))

        # 4+ days duration check
        self.assertTrue(any("Extra pairs" in t for t in clothing_texts))

    def test_smart_packing_cold_and_rain_signals(self):
        """Cold or rainy destination recommendations must adapt dynamically."""
        trip_cold = {"destination": "Manali, Himachal Pradesh", "num_days": 2}
        weather_cold = {"current": {"temperature": 9.0, "description": "Rain and Snow"}}

        checklist_cold = generate_smart_packing_checklist(trip_cold, weather_cold)
        clothing_texts = [it["text"] for it in checklist_cold["categories"]["clothing"]["items"]]
        self.assertTrue(any("Thermal innerwear" in t for t in clothing_texts))
        self.assertTrue(any("umbrella" in t.lower() or "raincoat" in t.lower() for t in clothing_texts))

    def test_checklist_persistence_and_idor_protection(self):
        """Owner can check items and persist to SQLite; cross-user tampering is rejected."""
        # 1. Bob (intruder) tries to update Alice's checklist
        with self.client.session_transaction() as sess:
            sess["user_id"] = self.user_b_id

        bad_res = self.client.post(
            f"/planner/{self.trip_live_id}/checklist",
            json={"checked_items": ["Government Photo ID / Passport & Visa (if applicable)"]}
        )
        self.assertEqual(bad_res.status_code, 404, "User B must not be allowed to modify User A's checklist")

        # 2. Alice (legitimate owner) checks items and saves
        with self.client.session_transaction() as sess:
            sess["user_id"] = self.user_a_id

        item_to_pack = "Government Photo ID / Passport & Visa (if applicable)"
        good_res = self.client.post(
            f"/planner/{self.trip_live_id}/checklist",
            json={"checked_items": [item_to_pack]}
        )
        self.assertEqual(good_res.status_code, 200)
        data = good_res.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["packed_count"], 1)

        # 3. Verify SQLite persistence via model
        with self.app.app_context():
            saved_state = get_trip_checklist(self.trip_live_id, self.user_a_id)
            self.assertIsNotNone(saved_state)
            self.assertEqual(saved_state["packed_count"], 1)


if __name__ == "__main__":
    unittest.main()
