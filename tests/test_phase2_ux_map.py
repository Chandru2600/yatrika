"""
Phase 2 Traveler UX Polish & Synchronization Regression Test Suite

Verifies:
1. Bidirectional MapLibre and itinerary synchronization contracts (frontend hooks, marker registration, coordinate jitter for duplicates, missing coordinate defense).
2. IBM Granite fallback and PDF service currency normalization (INR/₹ consistency, comfort budget threshold evaluation at ₹2,500/day, local transport ₹100-350).
3. Mobile itinerary reordering and persistence via /planner/<id>/update_planner (slot movement, authorization check, persistence to SQLite itinerary_json across reload).
"""

import os
import tempfile
import unittest
import json
import re

from app import create_app
from backend.database.db import init_db
from backend.models.user import create_user
from backend.models.trip import create_trip, get_trip_by_id, update_trip_itinerary
from backend.services.granite.granite_service import _parse_budget_hotels


class Phase2UXMapTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Create an isolated temporary SQLite database
        cls.test_db_fd, cls.test_db_path = tempfile.mkstemp(suffix="_phase2_test.db")
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
            self.user1_id = create_user("Alice Traveler", "alice_p2@test.local", "Password123!", role="user")
            self.user2_id = create_user("Bob Traveler", "bob_p2@test.local", "Password123!", role="user")

            # Initial itinerary with planned activities
            initial_itinerary = {
                "destination": "Goa",
                "days": [
                    {
                        "day": 1,
                        "date": "Day 1",
                        "theme": "Exploring Goa",
                        "morning": {
                            "activity": "Fort Aguada",
                            "place": "Fort Aguada",
                            "duration": "2h",
                            "entry_fee": "₹50",
                            "places": [
                                {
                                    "id": "aguada_1",
                                    "name": "Fort Aguada",
                                    "category": "Historical",
                                    "dur": "2h",
                                    "fee": 50,
                                    "lat": 15.4920,
                                    "lon": 73.7737
                                }
                            ]
                        },
                        "afternoon": {
                            "activity": "Calangute Beach",
                            "place": "Calangute Beach",
                            "duration": "3h",
                            "entry_fee": "Free",
                            "places": [
                                {
                                    "id": "calangute_1",
                                    "name": "Calangute Beach",
                                    "category": "Beach",
                                    "dur": "3h",
                                    "fee": 0,
                                    "lat": 15.5439,
                                    "lon": 73.7553
                                }
                            ]
                        },
                        "evening": None
                    }
                ],
                "selected_attractions": [
                    {"id": "aguada_1", "name": "Fort Aguada", "lat": 15.4920, "lon": 73.7737, "fee": 50},
                    {"id": "calangute_1", "name": "Calangute Beach", "lat": 15.5439, "lon": 73.7553, "fee": 0}
                ]
            }

            self.trip1_id = create_trip(self.user1_id, {
                "destination": "Goa",
                "start_date": "2026-11-10",
                "end_date": "2026-11-12",
                "num_days": 2,
                "budget": 20000,
                "num_travelers": 2,
                "travel_style": "comfort",
                "transport": "car",
                "transit_mode": "car"
            })
            # Persist initial itinerary into the trip row
            update_trip_itinerary(
                self.trip1_id,
                initial_itinerary,
                {},
                {"total_budget": 20000, "breakdown": {}},
                {}
            )

    def tearDown(self):
        with self.app.app_context():
            from backend.database.db import execute_query
            execute_query("DELETE FROM expenses")
            execute_query("DELETE FROM saved_trips")
            execute_query("DELETE FROM trips")
            execute_query("DELETE FROM users")

    # =========================================================================
    # Task 2: Legacy IBM Granite Fallback & PDF Currency Tests
    # =========================================================================

    def test_granite_fallback_currency_is_inr_and_uses_inr_comfort_threshold(self):
        """Granite service fallback must return INR currency and assess budget based on ₹2,500/day."""
        # Call fallback parser with mock inputs: 15,000 for 3 days -> 5,000/day > 2,500/day comfort threshold
        budget_data, hotels_data, transport_data = _parse_budget_hotels(
            text="", dest="Goa", days=3, travelers=2, total=15000, style="comfort", transport="car"
        )

        self.assertIn("currency", budget_data)
        self.assertEqual(budget_data["currency"], "INR", "Fallback currency must be INR, not USD")

        self.assertIn("budget_status", budget_data)
        # 15000 total > 3 days * 2500 (7500) -> comfortable
        self.assertEqual(budget_data["budget_status"], "comfortable")

        # Test tight budget under INR threshold: 3000 total < 3 * 2500 -> tight
        tight_budget, _, _ = _parse_budget_hotels(
            text="", dest="Goa", days=3, travelers=2, total=3000, style="budget", transport="bus"
        )
        self.assertEqual(tight_budget["budget_status"], "tight")

        # Verify transport tips are in INR
        local_transport = transport_data.get("local_transport", [])
        for item in local_transport:
            cost = item.get("cost_range", "")
            self.assertIn("₹", cost, f"Cost range should contain ₹ symbol: {cost}")
            self.assertNotIn("$", cost, f"USD symbol should not appear in local transport fallback: {cost}")

    def test_pdf_service_uses_inr_and_rupee_symbol(self):
        """PDF generation service source code and template must use INR/₹ consistently."""
        pdf_service_path = os.path.join(self.app.root_path, "backend", "services", "pdf", "pdf_service.py")
        self.assertTrue(os.path.exists(pdf_service_path), f"File not found: {pdf_service_path}")

        with open(pdf_service_path, "r", encoding="utf-8") as f:
            pdf_code = f.read()

        self.assertIn("INR", pdf_code, "PDF cover data must display INR currency")
        self.assertIn("Amount (INR)", pdf_code, "PDF table headers must specify Amount (INR)")
        self.assertIn('₹', pdf_code, "PDF service must use ₹ symbol for budget and hotel prices")
        # Ensure hardcoded '$' does not appear in budget or hotel formatting
        self.assertNotIn('f"${daily_budget', pdf_code)
        self.assertNotIn('f"${spent_str', pdf_code)
        self.assertNotIn('f"${h.get(\'price_per_night\'', pdf_code)


    # =========================================================================
    # Task 3: Mobile Itinerary Reordering & Persistence Tests
    # =========================================================================

    def test_update_planner_persists_reordered_itinerary(self):
        """Owner can reorder itinerary items and changes persist in SQLite database."""
        with self.client.session_transaction() as sess:
            sess["user_id"] = self.user1_id

        # Reorder activities: move Calangute Beach to morning and Fort Aguada to afternoon
        new_day_planner = {
            "1": {
                "morning": [
                    {
                        "id": "calangute_1",
                        "name": "Calangute Beach",
                        "dur": "3h",
                        "fee": 0,
                        "category": "Beach",
                        "lat": 15.5439,
                        "lon": 73.7553
                    }
                ],
                "afternoon": [
                    {
                        "id": "aguada_1",
                        "name": "Fort Aguada",
                        "dur": "2h",
                        "fee": 50,
                        "category": "Historical",
                        "lat": 15.4920,
                        "lon": 73.7737
                    }
                ],
                "evening": []
            }
        }

        resp = self.client.post(
            f"/planner/{self.trip1_id}/update_planner",
            json={"day_planner": new_day_planner},
            headers={"Content-Type": "application/json"}
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data.get("success"), f"Expected success: true, got {data}")

        # Verify DB directly to confirm persistence across server reload
        with self.app.app_context():
            updated_trip = get_trip_by_id(self.trip1_id)
            saved_itin = json.loads(updated_trip["itinerary_json"])

            # Verify day 1 morning is now Calangute Beach
            day1 = saved_itin["days"][0]
            self.assertEqual(day1["morning"]["activity"], "Calangute Beach")
            self.assertEqual(day1["morning"]["places"][0]["id"], "calangute_1")

            # Verify day 1 afternoon is now Fort Aguada
            self.assertEqual(day1["afternoon"]["activity"], "Fort Aguada")
            self.assertEqual(day1["afternoon"]["places"][0]["id"], "aguada_1")

            # Verify day_planner dictionary was stored
            self.assertIn("day_planner", saved_itin)
            self.assertEqual(saved_itin["day_planner"]["1"]["morning"][0]["id"], "calangute_1")

    def test_update_planner_idor_protection(self):
        """User B (Bob) must not be allowed to modify User A's (Alice) itinerary layout."""
        with self.client.session_transaction() as sess:
            sess["user_id"] = self.user2_id  # Bob is logged in

        malicious_payload = {
            "day_planner": {
                "1": {
                    "morning": [{"id": "hack", "name": "Vandalized Activity"}],
                    "afternoon": [],
                    "evening": []
                }
            }
        }

        resp = self.client.post(
            f"/planner/{self.trip1_id}/update_planner",
            json=malicious_payload,
            headers={"Content-Type": "application/json"}
        )
        # Should return 404 (or 403) with error message
        self.assertIn(resp.status_code, [403, 404])
        data = resp.get_json()
        self.assertFalse(data.get("success"))

        # Verify Alice's trip itinerary in DB remains uncorrupted
        with self.app.app_context():
            trip = get_trip_by_id(self.trip1_id)
            saved_itin = json.loads(trip["itinerary_json"])
            self.assertNotEqual(saved_itin["days"][0]["morning"]["activity"], "Vandalized Activity")

    # =========================================================================
    # Task 1: Bidirectional Map-Card Synchronization Contract Tests
    # =========================================================================

    def test_frontend_template_includes_interactive_card_attributes(self):
        """view_trip.html must render interactive data attributes and onclick map sync handlers."""
        template_path = os.path.join(self.app.root_path, "frontend", "templates", "planner", "view_trip.html")
        self.assertTrue(os.path.exists(template_path))

        with open(template_path, "r", encoding="utf-8") as f:
            tmpl = f.read()

        # Verify CSS classes
        self.assertIn(".activity-card-interactive", tmpl)
        self.assertIn(".activity-card-highlighted", tmpl)
        self.assertIn(".btn-reorder-move", tmpl)

        # Verify data attributes and click hooks on itinerary slots
        self.assertIn('onclick="window.focusCardElementOnMap(this)"', tmpl)
        self.assertIn('data-lat="', tmpl)
        self.assertIn('data-lon="', tmpl)
        self.assertIn('data-name="', tmpl)

    def test_trip_view_js_implements_bidirectional_sync_and_duplicate_jitter(self):
        """trip_view.js must define sync functions, duplicate offset logic, and missing coordinate handling."""
        js_path = os.path.join(self.app.root_path, "frontend", "static", "js", "trip_view.js")
        self.assertTrue(os.path.exists(js_path))


        with open(js_path, "r", encoding="utf-8") as f:
            js = f.read()

        # Verify reordering logic
        self.assertIn("window.reorderPlannedActivity =", js)
        self.assertIn("window.savePlannerChangesToServer =", js)

        # Verify map focus functions
        self.assertIn("window.focusCardElementOnMap =", js)
        self.assertIn("window.focusActivityOnMap =", js)
        self.assertIn("window.highlightAndScrollToActivity =", js)

        # Verify missing coordinates handling
        self.assertIn("Location coordinates unavailable", js)
        self.assertIn("!isFinite(origLat) || !isFinite(origLon)", js)

        # Verify duplicate coordinate jitter / offset handling
        self.assertIn("coordCounts", js)
        self.assertIn("plotLat +=", js)
        self.assertIn("plotLon +=", js)

        # Verify MapLibre resize trigger on tab activation
        self.assertIn('shown.bs.tab', js)
        self.assertIn('State.mapInstance.resize()', js)


if __name__ == "__main__":
    unittest.main()
