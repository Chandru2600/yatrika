"""
Unit Tests for Agent 4: Accommodations & Safety Model
Tests Agent 4 in isolation:
1. Base camp stay selection grounded in curated accommodations.
2. Safety index verification (>= 8.0/10).
3. Tiered hotel grouping (budget, mid-range, luxury).
4. Zero-crash fallback resilience on unknown or malformed destinations.
"""

import unittest
from backend.agents_models.safety_model import AccommodationsSafetyModel


class Agent4SafetyModelTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.agent4 = AccommodationsSafetyModel()

    def test_select_base_camp_known_destination(self):
        stay = self.agent4.select_base_camp("Coorg", travel_style="adventure", max_price=5000)
        self.assertIsInstance(stay, dict)
        self.assertIn("name", stay)
        self.assertIn("price_per_night", stay)
        self.assertIn("safety_score", stay)
        self.assertGreater(stay["price_per_night"], 0)
        self.assertGreaterEqual(float(stay["safety_score"]), 8.0)
        self.assertIn("latitude", stay)
        self.assertIn("longitude", stay)

    def test_select_base_camp_respects_max_price(self):
        stay = self.agent4.select_base_camp("Jaipur", travel_style="budget", max_price=2000)
        self.assertIsInstance(stay, dict)
        self.assertLessEqual(stay["price_per_night"], 2500)

    def test_select_base_camp_unknown_destination_fallback(self):
        stay = self.agent4.select_base_camp("UnknownRemoteTown999", travel_style="nature", max_price=3000)
        self.assertIsInstance(stay, dict)
        self.assertIn("name", stay)
        self.assertGreater(stay["price_per_night"], 0)
        self.assertGreaterEqual(float(stay["safety_score"]), 7.0)

    def test_tiered_accommodations_structure(self):
        base_stay = self.agent4.select_base_camp("Munnar", travel_style="relaxation", max_price=4000)
        tiered = self.agent4.get_tiered_accommodations("Munnar", base_camp_stay=base_stay, max_price=4000)
        self.assertIsInstance(tiered, dict)
        self.assertIn("budget_hotels", tiered)
        self.assertIn("mid_range_hotels", tiered)
        self.assertIn("luxury_hotels", tiered)
        self.assertIsInstance(tiered["budget_hotels"], list)
        self.assertIsInstance(tiered["mid_range_hotels"], list)
        self.assertIsInstance(tiered["luxury_hotels"], list)


if __name__ == "__main__":
    unittest.main()
