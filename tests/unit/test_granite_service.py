"""
Unit Tests for IBM Granite Service Fallback & Zero-Crash Resilience
Tests Granite integration in isolation:
1. When IBM watsonx.ai credentials are missing / empty, service must seamlessly fall back.
2. Zero-crash guarantee: no unhandled exceptions under any inputs.
3. Output plan structure adheres strictly to expected travel dossier contract:
   itinerary, budget, hotels, transit, booking_links, emergency.
"""

import os
import unittest
from unittest.mock import patch

from backend.services.granite.granite_service import generate_complete_travel_plan


class GraniteServiceUnitTestCase(unittest.TestCase):
    def test_generate_plan_no_credentials_fallback(self):
        """Service must use local multi-agent pipeline + destination profiles when IBM creds are unset."""
        with patch.dict(os.environ, {"IBM_API_KEY": "", "IBM_PROJECT_ID": ""}):
            trip_data = {
                "destination": "Coorg",
                "source": "Bengaluru",
                "num_days": 3,
                "num_travelers": 2,
                "budget": 22000,
                "travel_style": "adventure",
                "transport": "train",
                "start_date": "2026-11-01"
            }
            plan = generate_complete_travel_plan(trip_data)

            self.assertIsInstance(plan, dict)
            self.assertIn("itinerary", plan)
            self.assertIn("budget", plan)
            self.assertIn("hotels", plan)
            self.assertIn("transit", plan)
            self.assertIn("booking_links", plan)
            self.assertIn("emergency", plan)

            # Validate itinerary days
            days = plan["itinerary"].get("days", [])
            self.assertEqual(len(days), 3)
            for d in days:
                self.assertIn("morning", d)
                self.assertIn("afternoon", d)
                self.assertIn("evening", d)

    def test_generate_plan_zero_crash_on_edge_inputs(self):
        """Zero crash resilience on strange/minimal destination strings or extreme inputs."""
        with patch.dict(os.environ, {"IBM_API_KEY": "", "IBM_PROJECT_ID": ""}):
            for weird_dest in ("", "   ", "RemotePeak999", "Goa, India"):
                trip_data = {
                    "destination": weird_dest,
                    "num_days": 2,
                    "num_travelers": 1,
                    "budget": 10000,
                    "travel_style": "budget",
                    "transport": "bus"
                }
                plan = generate_complete_travel_plan(trip_data)
                self.assertIsInstance(plan, dict)
                self.assertIn("itinerary", plan)


if __name__ == "__main__":
    unittest.main()
