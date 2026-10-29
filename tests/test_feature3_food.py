"""
Feature 3 Tests - Data-Driven Food Layer & Must-Try Dishes
Verifies:
1. Data-driven loading from data/food_guide.csv.
2. Direct city match (e.g. Coorg, Jaipur, Goa).
3. State-level fallback when city is missing.
4. Pan-India default fallback when destination is completely unknown.
5. Daily meal stops (1-2 per day) with eatery name, specialty, price, and landmark.
6. Zero crash resilience against empty, malformed, or missing inputs.
"""

import unittest
from backend.services.food.food_service import (
    get_food_for_destination,
    attach_food_layer_to_itinerary
)


class Feature3FoodTestCase(unittest.TestCase):
    def test_city_level_food_match(self):
        food = get_food_for_destination("Coorg", num_days=3)
        self.assertEqual(food["matched_level"], "city")
        self.assertTrue(len(food["must_try_dishes"]) >= 2)
        # Verify Kodava specialties
        dish_str = " ".join(food["must_try_dishes"]).lower()
        self.assertTrue("pandi curry" in dish_str or "akki roti" in dish_str)

        # Check day-wise meal stops
        day_meals = food["day_meals"]
        self.assertEqual(len(day_meals), 3)
        for dm in day_meals:
            stops = dm["meal_stops"]
            self.assertTrue(len(stops) >= 1)
            stop = stops[0]
            self.assertIn("eatery", stop)
            self.assertIn("specialty", stop)
            self.assertIn("price_range", stop)
            self.assertIn("landmark", stop)
            self.assertTrue(float(stop["rating"]) > 0)

    def test_state_level_fallback(self):
        # A destination in Rajasthan not explicitly a city in CSV
        food = get_food_for_destination("Bikaner, Rajasthan", num_days=2)
        self.assertIn(food["matched_level"], ["city", "state"])
        self.assertTrue(len(food["must_try_dishes"]) > 0)
        dish_str = " ".join(food["must_try_dishes"]).lower()
        self.assertTrue("dal baati" in dish_str or "thali" in dish_str or "rajasthan" in dish_str)

    def test_pan_india_default_fallback(self):
        # Completely unknown location
        food = get_food_for_destination("Atlantis Unknown Island", num_days=3)
        self.assertEqual(food["matched_level"], "default")
        self.assertTrue(len(food["must_try_dishes"]) > 0)
        self.assertEqual(len(food["day_meals"]), 3)

    def test_attach_food_layer_to_itinerary(self):
        itinerary = {
            "days": [
                {"day": 1, "title": "Day 1 Loop"},
                {"day": 2, "title": "Day 2 Loop"}
            ]
        }
        res = attach_food_layer_to_itinerary(itinerary, "Goa, India")
        self.assertIn("food_guide", res)
        self.assertTrue(len(res["days"]) == 2)
        for d in res["days"]:
            self.assertIn("must_try_dishes", d)
            self.assertIn("food_recommendations", d)
            self.assertTrue(len(d["food_recommendations"]) >= 1)

    def test_zero_crash_on_bad_inputs(self):
        # None and empty inputs
        res1 = attach_food_layer_to_itinerary({}, "")
        self.assertIsInstance(res1, dict)

        res2 = attach_food_layer_to_itinerary(None, None)
        self.assertIsNone(res2)

        res3 = get_food_for_destination("", num_days=-5)
        self.assertIsInstance(res3, dict)
        self.assertTrue(len(res3["must_try_dishes"]) > 0)
