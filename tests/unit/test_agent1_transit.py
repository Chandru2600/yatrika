"""
Unit Tests for Agent 1: Geospatial & Transit Model
Tests Agent 1 in isolation:
1. Door-to-door transit calculation across transport modes (train, bus, flight, car).
2. Grounded fare and transit time calculation.
3. Stay-to-POI Haversine distance matrix computation.
4. Resilience against edge-case coordinates and missing fields.
"""

import unittest
from backend.agents_models.geospatial_model import GeospatialTransitModel


class Agent1GeospatialTransitTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.agent1 = GeospatialTransitModel()
        cls.sample_stay = {
            "name": "Heritage Kodagu Estate Resort",
            "city": "Madikeri",
            "latitude": 12.4244,
            "longitude": 75.7382,
            "price_per_night": 2800
        }

    def test_transit_modes_calculation(self):
        for mode in ("train", "bus", "flight", "car"):
            res = self.agent1.calculate_door_to_door_transit(
                source="Bengaluru",
                destination="Coorg",
                stay_info=self.sample_stay,
                travelers=2,
                selected_mode=mode
            )
            self.assertIsInstance(res, dict)
            self.assertIn("legs", res)
            self.assertIn("estimated_fare_inr", res)
            self.assertIn("duration_str", res)
            self.assertGreater(float(res["estimated_fare_inr"]), 0)

    def test_stay_to_poi_matrix(self):
        raw_pois = [
            {"id": "p1", "name": "Abbey Falls", "lat": 12.4540, "lon": 75.7180},
            {"id": "p2", "name": "Raja's Seat", "lat": 12.4180, "lon": 75.7380}
        ]
        enriched = self.agent1.calculate_stay_to_poi_matrix(self.sample_stay, raw_pois)
        self.assertIsInstance(enriched, list)
        self.assertEqual(len(enriched), 2)
        for p in enriched:
            self.assertIn("distance_from_stay_km", p)
            self.assertGreater(float(p["distance_from_stay_km"]), 0)

    def test_transit_resilience_missing_stay_coords(self):
        incomplete_stay = {"name": "Simple Homestay"}
        res = self.agent1.calculate_door_to_door_transit(
            source="Mumbai",
            destination="Goa",
            stay_info=incomplete_stay,
            travelers=1,
            selected_mode="train"
        )
        self.assertIsInstance(res, dict)
        self.assertIn("estimated_fare_inr", res)
        self.assertGreater(float(res["estimated_fare_inr"]), 0)


if __name__ == "__main__":
    unittest.main()
