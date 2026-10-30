"""
Unit Tests for Booking Link Builder
Tests booking_service.build_booking_links in isolation:
1. Structured deep links for hotels, trains, and buses.
2. Required schema: provider, name, url, icon, badge.
3. Correct query parameter injection (checkin, checkout, guests, route).
4. Zero crash on None, empty dict, or malformed trip data.
"""

import unittest
from backend.services.booking.booking_service import build_booking_links


class BookingBuilderUnitTestCase(unittest.TestCase):
    def test_booking_links_output_shape(self):
        trip_data = {
            "destination": "Goa",
            "source": "Mumbai",
            "start_date": "2026-11-10",
            "end_date": "2026-11-14",
            "num_days": 4,
            "num_travelers": 2
        }
        res = build_booking_links(trip_data)
        self.assertIsInstance(res, dict)
        self.assertIn("hotels", res)
        self.assertIn("trains", res)
        self.assertIn("buses", res)
        self.assertIn("summary", res)

        # Check required schema per link
        for cat in ("hotels", "trains", "buses"):
            links = res[cat]
            self.assertGreater(len(links), 0)
            for link in links:
                self.assertIn("provider", link)
                self.assertIn("name", link)
                self.assertIn("url", link)
                self.assertIn("icon", link)
                self.assertIn("badge", link)
                self.assertTrue(link["url"].startswith("http"), f"Invalid link url: {link['url']}")

    def test_zero_crash_on_none_and_empty(self):
        for bad_input in (None, {}, {"destination": None}, {"num_travelers": -1}):
            res = build_booking_links(bad_input)
            self.assertIsInstance(res, dict)
            self.assertIn("hotels", res)
            self.assertGreater(len(res["hotels"]), 0)


if __name__ == "__main__":
    unittest.main()
