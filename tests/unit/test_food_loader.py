"""
Unit Tests for Food Guide Loader
Tests backend/services/food/food_service.py in isolation:
1. Exact city hit match (e.g. Coorg, Jaipur, Goa).
2. State-level fallback match when city has no direct rows.
3. Pan-India safe fallback for unlisted or remote destinations.
4. Output structure adheres to food guide schema: must_try_dishes, day_meals, meal_stops.
"""

import unittest
from backend.services.food.food_service import (
    get_food_for_destination,
    attach_food_layer_to_itinerary
)


class FoodLoaderUnitTestCase(unittest.TestCase):
    def test_city_level_hit(self):
        food_coorg = get_food_for_destination("Coorg", num_days=3)
        self.assertIsInstance(food_coorg, dict)
        self.assertEqual(food_coorg["matched_level"], "city")
        self.assertTrue(len(food_coorg["must_try_dishes"]) >= 2)
        dish_str = " ".join(food_coorg["must_try_dishes"]).lower()
        self.assertTrue("pandi curry" in dish_str or "akki roti" in dish_str or "coorg" in dish_str)

        self.assertEqual(len(food_coorg["day_meals"]), 3)
        first_meal_stop = food_coorg["day_meals"][0]["meal_stops"][0]
        self.assertIn("eatery", first_meal_stop)
        self.assertIn("specialty", first_meal_stop)
        self.assertIn("price_range", first_meal_stop)

    def test_state_level_fallback(self):
        food_state = get_food_for_destination("Bikaner, Rajasthan", num_days=2)
        self.assertIsInstance(food_state, dict)
        self.assertIn(food_state["matched_level"], ["city", "state"])
        self.assertTrue(len(food_state["must_try_dishes"]) > 0)

    def test_pan_india_fallback(self):
        food_unknown = get_food_for_destination("NonExistentTown999, UnknownState", num_days=3)
        self.assertIsInstance(food_unknown, dict)
        self.assertEqual(food_unknown["matched_level"], "default")
        self.assertTrue(len(food_unknown["must_try_dishes"]) > 0)
        self.assertEqual(len(food_unknown["day_meals"]), 3)

    def test_attach_food_layer_to_itinerary(self):
        sample_itinerary = {
            "days": [
                {"day": 1, "title": "Day 1 Loop"},
                {"day": 2, "title": "Day 2 Loop"}
            ]
        }
        enriched = attach_food_layer_to_itinerary(sample_itinerary, "Coorg")
        self.assertIn("food_guide", enriched)
        self.assertIn("must_try_dishes", enriched["food_guide"])
        for day in enriched["days"]:
            self.assertIn("food_recommendations", day)
            self.assertIn("must_try_dishes", day)


if __name__ == "__main__":
    unittest.main()
