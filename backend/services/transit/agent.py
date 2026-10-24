"""
TravelPlannerAgent - Custom Autonomous Inter-City Transit Agent (InterCityTransitAgent)
Major Project Custom AI Agent Module.
Combines Indian Perception Dataset, Live API Feeds, Multi-Criteria Optimization Engine,
Travel Planner Agent LLM Synthesis, and Day-1 Timeline Auto-Lock logic.
"""

import os
import json
import math
from typing import Dict, Any
from backend.services.granite.granite_service import call_granite

# Path to perception dataset
DATASET_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "database", "transit_dataset.json")


class InterCityTransitAgent:
    """
    Autonomous AI Agent for Inter-City Transit Perception, Reasoning & Planning.
    """

    def __init__(self):
        self.dataset = self._load_dataset()

    def _load_dataset(self) -> Dict[str, Any]:
        """Load transit perception dataset."""
        try:
            if os.path.exists(DATASET_PATH):
                with open(DATASET_PATH, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass
        return {
            "cities": {},
            "carbon_emissions_g_per_km": {"train": 14.2, "bus": 22.5, "car": 112.0, "bike": 38.0, "flight": 158.0},
            "comfort_scores": {}
        }

    def perceive_city_context(self, city_name: str) -> Dict[str, Any]:
        """Extract city perception attributes from dataset."""
        c_clean = city_name.strip().lower()
        cities = self.dataset.get("cities", {})
        for key, info in cities.items():
            if key in c_clean or c_clean in key:
                return info
        return {
            "name": city_name.title(),
            "rail": f"{city_name[:3].upper()}",
            "air": f"{city_name[:3].upper()}",
            "bus": f"{city_name.title()} Bus Station",
            "cab_base_rate": 350,
            "transfer_time_mins": 35
        }

    def compute_carbon_footprint(self, mode: str, dist_km: float, travelers: int) -> float:
        """Compute total trip carbon emissions in kg CO2."""
        factors = self.dataset.get("carbon_emissions_g_per_km", {})
        g_per_km = factors.get(mode.lower(), 25.0)
        total_g = g_per_km * dist_km * travelers
        return round(total_g / 1000.0, 1)

    def calculate_door_to_door(self, mode: str, main_duration_str: str, source_city: str, dest_city: str) -> Dict[str, Any]:
        """Calculate door-to-door travel duration and transfer cab costs."""
        src_info = self.perceive_city_context(source_city)
        dst_info = self.perceive_city_context(dest_city)

        first_mile_cab = src_info.get("cab_base_rate", 350)
        last_mile_cab = dst_info.get("cab_base_rate", 350)

        first_mile_mins = src_info.get("transfer_time_mins", 35)
        last_mile_mins = dst_info.get("transfer_time_mins", 35)

        # Parse main duration
        main_mins = 240
        try:
            parts = main_duration_str.split()
            h = int(parts[0].replace('h', '')) if len(parts) > 0 else 4
            m = int(parts[1].replace('m', '')) if len(parts) > 1 else 0
            main_mins = h * 60 + m
        except Exception:
            pass

        if mode in ["car", "bike"]:
            total_cab_cost = 0
            total_mins = main_mins + 15
        else:
            total_cab_cost = first_mile_cab + last_mile_cab
            total_mins = main_mins + first_mile_mins + last_mile_mins

        tot_h = total_mins // 60
        tot_m = total_mins % 60

        return {
            "first_mile_cab": first_mile_cab if mode not in ["car", "bike"] else 0,
            "last_mile_cab": last_mile_cab if mode not in ["car", "bike"] else 0,
            "total_transfer_cab_cost": total_cab_cost,
            "door_to_door_duration": f"{tot_h}h {tot_m}m",
            "door_to_door_mins": total_mins
        }

    def evaluate_multi_criteria_reasoning(self, all_options: Dict[str, Any], total_budget: float,
                                          travelers: int, travel_style: str = "balanced") -> Dict[str, Any]:
        """
        Custom Multi-Criteria Optimization Engine.
        Scores modes based on Budget Impact, Time Efficiency, Comfort Tier, and Carbon Footprint.
        """
        weights_map = {
            "budget": {"cost": 0.55, "time": 0.15, "comfort": 0.15, "eco": 0.15},
            "luxury": {"cost": 0.10, "time": 0.30, "comfort": 0.50, "eco": 0.10},
            "fast": {"cost": 0.15, "time": 0.60, "comfort": 0.15, "eco": 0.10},
            "balanced": {"cost": 0.30, "time": 0.30, "comfort": 0.25, "eco": 0.15}
        }
        w = weights_map.get(travel_style.lower(), weights_map["balanced"])

        scores = {}
        max_cost = max([opt["total_cost"] for opt in all_options.values()] or [10000])
        min_cost = min([opt["total_cost"] for opt in all_options.values()] or [500])

        for mode, opt in all_options.items():
            # Cost score (inverse)
            cost_val = opt["total_cost"]
            cost_score = 10.0 * (1.0 - (cost_val - min_cost) / (max_cost - min_cost + 1.0))

            # Comfort score
            cls = opt.get("selected_class", "")
            comfort_table = self.dataset.get("comfort_scores", {}).get(mode, {})
            comfort_score = comfort_table.get(cls, 7.0)

            # Eco score (inverse emissions)
            eco_kg = opt.get("carbon_footprint_kg", 50.0)
            eco_score = max(1.0, 10.0 - (eco_kg / 15.0))

            # Time score (inverse duration)
            dur_str = opt.get("travel_duration", "5h 0m")
            try:
                h = int(dur_str.split()[0].replace('h', ''))
            except Exception:
                h = 5
            time_score = max(1.0, 10.0 - (h * 0.75))

            # Hub Feasibility Bonus/Penalty: direct terminal vs 100km cab transfer
            has_direct = opt.get("has_direct_hub", True)
            direct_penalty = 0.0 if has_direct else -2.5

            total_score = (w["cost"] * cost_score +
                           w["time"] * time_score +
                           w["comfort"] * comfort_score +
                           w["eco"] * eco_score) + direct_penalty
            scores[mode] = round(max(0.5, total_score), 2)

        best_mode = max(scores, key=scores.get) if scores else "bus"
        return {
            "scores": scores,
            "recommended_mode": best_mode
        }

    def generate_granite_tradeoff_rationale(self, chosen: Dict[str, Any], all_options: Dict[str, Any],
                                           source: str, dest: str, travelers: int, budget: float) -> str:
        """
        Use IBM Granite LLM to generate intelligent human-like trade-off advice.
        """
        prompt = (
            f"You are the Inter-City Transit Agent for a trip from {source} to {dest} for {travelers} traveler(s) with total budget Rs. {budget}.\n"
            f"Chosen Transport: {chosen.get('mode_title', chosen['mode'])}\n"
            f"Total Cost: Rs. {chosen['total_cost']} (Rs. {chosen['total_cost']//travelers} per person)\n"
            f"Arrival Time: {chosen['arrival_time']}\n"
            f"Location Notice: {chosen.get('location_notice', 'Direct Service')}\n"
            f"Provide a concise 2-sentence AI Advisor recommendation explaining why this mode is optimal for reaching {dest}."
        )

        try:
            granite_text = call_granite(prompt, max_tokens=150)
            if granite_text and len(granite_text.strip()) > 20:
                return granite_text.strip()
        except Exception:
            pass

        # Fallback intelligent agent rationale with location awareness
        savings = budget - chosen['total_cost']
        pct = round((chosen['total_cost'] / budget) * 100, 1)
        notice = chosen.get("location_notice", "")

        return (
            f"[AI Agent Recommendation] {chosen.get('mode_title', chosen['mode'].title())} is optimal for your trip to {dest.title()}. "
            f"It consumes {pct}% of your budget (Rs. {chosen['total_cost']}), leaving Rs. {savings:,.0f} for local stay. "
            f"{notice}"
        )

    def run_agent_workflow(self, source: str, dest: str, all_options: Dict[str, Any],
                           selected_mode: str, travelers: int, total_budget: float,
                           travel_style: str = "balanced") -> Dict[str, Any]:
        """
        Main Agent Execution Lifecycle.
        Enriches options with carbon emissions, door-to-door metrics, multi-criteria scores,
        IBM Granite LLM synthesis, and Day 1 timeline locking status.
        """
        # 1. Perception & Enrichment
        for mode, opt in all_options.items():
            dist = opt.get("distance_km", 300.0)
            opt["carbon_footprint_kg"] = self.compute_carbon_footprint(mode, dist, travelers)
            opt["door_to_door"] = self.calculate_door_to_door(mode, opt.get("travel_duration", "5h 0m"), source, dest)

        # 2. Multi-Criteria Reasoning Optimization Core
        reasoning = self.evaluate_multi_criteria_reasoning(all_options, total_budget, travelers, travel_style)

        chosen_key = selected_mode.lower() if selected_mode.lower() in all_options else reasoning["recommended_mode"]
        chosen = all_options[chosen_key]

        # 3. Day 1 Timeline Auto-Lock Logic
        arr_time = chosen.get("arrival_time", "12:00")
        arr_hour = int(arr_time.split(":")[0]) if ":" in arr_time else 12
        is_afternoon_arrival = arr_hour >= 12

        lock_status = {
            "day1_morning_locked": is_afternoon_arrival,
            "lock_reason": f"Transit arrives at {arr_time}. Morning (08:00 AM - 01:00 PM) auto-locked as 'In Transit'." if is_afternoon_arrival else "Morning arrival. Day 1 schedule unlocked for morning sightseeing.",
            "hotel_checkin_recommended": f"{arr_hour + 1:02d}:00" if is_afternoon_arrival else "12:00"
        }

        # 4. IBM Granite Synthesis Rationale
        advisor_rationale = self.generate_granite_tradeoff_rationale(chosen, all_options, source, dest, travelers, total_budget)

        return {
            "agent_name": "InterCityTransitAgent v2.0",
            "source_perception": self.perceive_city_context(source),
            "dest_perception": self.perceive_city_context(dest),
            "multi_criteria_scores": reasoning["scores"],
            "ai_recommended_mode": reasoning["recommended_mode"],
            "ai_tradeoff_rationale": advisor_rationale,
            "timeline_lock_status": lock_status,
            "chosen_details": chosen
        }
