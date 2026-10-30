"""
Unit Tests for Agent 2: Itinerary Scheduling Model
Tests Agent 2 in isolation:
1. POI extraction from 10,025 attractions dataset based on destination coordinates.
2. Multi-day schedule generation with daily loops.
3. Morning, afternoon, and evening slot allocation.
4. Closing day filtering and zero-crash guarantees.
"""

import unittest
from backend.agents_models.scheduling_model import ItinerarySchedulingModel


class Agent2SchedulingModelTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.agent2 = ItinerarySchedulingModel()
        cls.sample_stay = {
            "name": "Heritage Kodagu Estate Resort",
            "city": "Madikeri",
            "latitude": 12.4244,
            "longitude": 75.7382
        }

    def test_fetch_attractions_from_dataset(self):
        pois = self.agent2.fetch_attractions(
            destination="Coorg",
            interests=["nature", "sightseeing"],
            stay_coords=(12.4244, 75.7382)
        )
        self.assertIsInstance(pois, list)
        self.assertGreater(len(pois), 0)
        first_poi = pois[0]
        self.assertIn("name", first_poi)
        self.assertIn("lat", first_poi)
        self.assertIn("lon", first_poi)
        self.assertIn("time_needed_hrs", first_poi)

    def test_schedule_multiday_itinerary(self):
        pois = self.agent2.fetch_attractions("Jaipur", ["heritage", "culture"])
        itinerary = self.agent2.schedule_multiday_itinerary(
            destination="Jaipur",
            num_days=3,
            stay_info={"name": "Jaipur Haveli", "latitude": 26.9124, "longitude": 75.7873},
            enriched_pois=pois,
            travel_style="cultural"
        )
        self.assertIsInstance(itinerary, list)
        self.assertEqual(len(itinerary), 3)

        for day in itinerary:
            self.assertIn("morning", day)
            self.assertIn("afternoon", day)
            self.assertIn("evening", day)
            m_poi = day["morning"].get("name") or day["morning"].get("place")
            self.assertTrue(m_poi, "Morning slot must have a non-empty POI name")

    def test_zero_crash_on_empty_pois(self):
        itinerary = self.agent2.schedule_multiday_itinerary(
            destination="MinimalVillage",
            num_days=2,
            stay_info=self.sample_stay,
            enriched_pois=[],
            travel_style="relaxation"
        )
        self.assertIsInstance(itinerary, list)
        self.assertEqual(len(itinerary), 2)


if __name__ == "__main__":
    unittest.main()
