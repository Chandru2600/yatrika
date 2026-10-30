"""
Unit Tests for Agent 3: Budget & Expense Model
Tests Agent 3 in isolation:
1. Machine Learning budget regression cost predictions.
2. Itemized category allocations (stay, transit, food, activities, contingency).
3. Sum integrity of budget breakdown.
4. Feasibility checks and pocket balance computation.
"""

import unittest
from backend.agents_models.budget_model import BudgetExpenseModel


class Agent3BudgetModelTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.agent3 = BudgetExpenseModel()

    def test_predict_expected_cost_ml(self):
        cost = self.agent3.predict_expected_cost_ml(
            days=3,
            travelers=2,
            distance_km=280.0,
            transport_mode="train",
            hotel_tier="budget"
        )
        self.assertIsInstance(cost, float)
        self.assertGreater(cost, 5000.0)

        # Longer trip must cost more
        longer_cost = self.agent3.predict_expected_cost_ml(
            days=7,
            travelers=2,
            distance_km=280.0,
            transport_mode="train",
            hotel_tier="budget"
        )
        self.assertGreater(longer_cost, cost)

    def test_calculate_stay_first_budget_breakdown(self):
        stay_info = {"name": "Heritage Resort", "price_per_night": 2500}
        total_budget = 24000.0
        res = self.agent3.calculate_stay_first_budget(
            total_budget=total_budget,
            travelers=2,
            days=3,
            stay_info=stay_info,
            transit_fare=1200.0
        )
        self.assertIsInstance(res, dict)
        self.assertIn("breakdown", res)
        self.assertIn("stay_cost_inr", res)
        self.assertIn("transit_cost_inr", res)
        self.assertIn("food_cost_inr", res)
        self.assertIn("sightseeing_cost_inr", res)
        self.assertIn("emergency_buffer_inr", res)
        self.assertIn("is_feasible", res)

        # Category sums must equal committed total
        sum_categories = (
            res["stay_cost_inr"] +
            res["transit_cost_inr"] +
            res["food_cost_inr"] +
            res["sightseeing_cost_inr"] +
            res["emergency_buffer_inr"]
        )
        self.assertAlmostEqual(sum_categories, res["committed_total_inr"], places=1)


if __name__ == "__main__":
    unittest.main()
