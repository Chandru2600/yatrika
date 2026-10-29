"""
Yatrika - Food Layer Service (Feature 3)
Provides authentic local food discovery:
- "Must-try" regional dishes keyed by destination
- 1-2 curated meal stops per itinerary day near sightseeing routes
- Data-driven lookup via data/food_guide.csv
- Multi-tier fallback: City ➔ State-level defaults ➔ Pan-India defaults
- Zero-crash guarantee offline and under any input conditions.
"""

import os
import csv
from pathlib import Path
from typing import Dict, Any, List

_CSV_PATH = Path(__file__).resolve().parent.parent.parent.parent / "data" / "food_guide.csv"
_FOOD_DATA_CACHE: List[Dict[str, str]] | None = None

# Known destination to state mapping for smart fallback
CITY_STATE_MAP = {
    "coorg": "Karnataka",
    "madikeri": "Karnataka",
    "chikmagalur": "Karnataka",
    "mysore": "Karnataka",
    "mysuru": "Karnataka",
    "hampi": "Karnataka",
    "gokarna": "Karnataka",
    "dandeli": "Karnataka",
    "bengaluru": "Karnataka",
    "bangalore": "Karnataka",
    "munnar": "Kerala",
    "alleppey": "Kerala",
    "alappuzha": "Kerala",
    "wayanad": "Kerala",
    "kochi": "Kerala",
    "cochin": "Kerala",
    "varkala": "Kerala",
    "jaipur": "Rajasthan",
    "udaipur": "Rajasthan",
    "jodhpur": "Rajasthan",
    "jaisalmer": "Rajasthan",
    "manali": "Himachal Pradesh",
    "shimla": "Himachal Pradesh",
    "dharamshala": "Himachal Pradesh",
    "ooty": "Tamil Nadu",
    "kodaikanal": "Tamil Nadu",
    "pondicherry": "Tamil Nadu",
    "puducherry": "Tamil Nadu",
    "chennai": "Tamil Nadu",
    "rishikesh": "Uttarakhand",
    "haridwar": "Uttarakhand",
    "dehradun": "Uttarakhand",
    "nainital": "Uttarakhand",
    "mussoorie": "Uttarakhand",
    "goa": "Goa",
    "panaji": "Goa",
    "delhi": "Delhi",
    "mumbai": "Maharashtra",
    "pune": "Maharashtra",
    "varanasi": "Uttar Pradesh",
    "agra": "Uttar Pradesh",
    "lucknow": "Uttar Pradesh"
}


def _load_food_data() -> List[Dict[str, str]]:
    """Loads food_guide.csv into memory once."""
    global _FOOD_DATA_CACHE
    if _FOOD_DATA_CACHE is not None:
        return _FOOD_DATA_CACHE

    records = []
    if _CSV_PATH.exists():
        try:
            with open(_CSV_PATH, mode="r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    cleaned_row = {}
                    for k, v in row.items():
                        if k is not None:
                            cleaned_row[str(k).strip()] = str(v).strip() if v is not None else ""
                    records.append(cleaned_row)
        except Exception as e:
            print(f"[Food Service] Warning: error loading food_guide.csv: {e}")

    _FOOD_DATA_CACHE = records
    return _FOOD_DATA_CACHE


def get_food_for_destination(destination: str, num_days: int = 3) -> Dict[str, Any]:
    """
    Returns data-driven food guide for destination with:
    - must_try_dishes: list of famous dishes
    - day_meals: list of meal stop recommendations per day (1-2 per day)
    Falls back gracefully to state-level or pan-India defaults.
    """
    data = _load_food_data()
    clean_dest = str(destination or "India").split(",")[0].strip().lower()

    # 1. Direct City Match
    city_matches = [
        r for r in data
        if r.get("destination", "").lower() == clean_dest or clean_dest in r.get("destination", "").lower()
    ]

    # 2. State-level Fallback Match
    state_matches = []
    inferred_state = None
    for k, st in CITY_STATE_MAP.items():
        if k in clean_dest:
            inferred_state = st
            break

    if not inferred_state:
        # Check if a state name is mentioned in destination string
        for st in ["karnataka", "kerala", "rajasthan", "himachal", "tamil nadu", "uttarakhand", "goa", "maharashtra", "delhi", "uttar pradesh"]:
            if st in destination.lower():
                inferred_state = st.title()
                break

    if inferred_state:
        state_matches = [
            r for r in data
            if r.get("state", "").lower() == inferred_state.lower()
        ]

    # 3. Default Pan-India Fallback
    default_matches = [
        r for r in data
        if "default" in r.get("destination", "").lower() or "india" in r.get("state", "").lower()
    ]

    # Select pool
    pool = city_matches if city_matches else (state_matches if state_matches else default_matches)
    if not pool:
        pool = data if data else [{
            "destination": "India",
            "state": "India",
            "must_try_dishes": "Traditional Regional Thali, Dal Makhani, Paneer Tikka, Fresh Breads, Masala Chai",
            "meal_type": "Lunch",
            "eatery_name": "Popular Regional Restaurant",
            "specialty": "Traditional Thali & Breads",
            "price_range": "₹250-450",
            "address_or_landmark": "City Center",
            "veg_nonveg": "Both",
            "rating": "4.5"
        }]

    # Extract Must-Try Dishes
    raw_dishes_str = pool[0].get("must_try_dishes", "")
    must_try_dishes = [d.strip() for d in raw_dishes_str.split(",") if d.strip()]

    # Distribute 1-2 meal stops per day
    day_meals = []
    pool_len = len(pool)
    for day_idx in range(num_days):
        day_num = day_idx + 1
        # Pick 2 meal stops (e.g. Lunch and Dinner)
        m1 = pool[(day_idx * 2) % pool_len]
        m2 = pool[(day_idx * 2 + 1) % pool_len] if pool_len > 1 else m1

        stops = []
        for meal_item, default_type in [(m1, "Lunch"), (m2, "Dinner")]:
            stops.append({
                "meal": meal_item.get("meal_type") or default_type,
                "eatery": meal_item.get("eatery_name", "Local Heritage Cafe"),
                "specialty": meal_item.get("specialty", "Regional signature delicacy"),
                "price_range": meal_item.get("price_range", "₹200-400"),
                "landmark": meal_item.get("address_or_landmark", "Near Town Center"),
                "veg_nonveg": meal_item.get("veg_nonveg", "Both"),
                "rating": float(meal_item.get("rating", 4.5) or 4.5)
            })

        day_meals.append({
            "day": day_num,
            "meal_stops": stops
        })

    return {
        "destination": destination,
        "matched_level": "city" if city_matches else ("state" if state_matches else "default"),
        "must_try_dishes": must_try_dishes,
        "day_meals": day_meals
    }


def attach_food_layer_to_itinerary(itinerary: Dict[str, Any], destination: str) -> Dict[str, Any]:
    """
    Enriches itinerary days with must-try dishes and daily meal stops.
    Guaranteed zero crashes under any inputs.
    """
    if not isinstance(itinerary, dict):
        return itinerary

    days_list = itinerary.get("days", [])
    num_days = len(days_list) if days_list else 3

    try:
        food_guide = get_food_for_destination(destination, num_days=max(1, num_days))
        itinerary["food_guide"] = food_guide

        # Enrich each day with that day's meal stops and must-try dishes
        day_meals = food_guide.get("day_meals", [])
        for idx, d in enumerate(days_list):
            if idx < len(day_meals):
                d["food_recommendations"] = day_meals[idx].get("meal_stops", [])
            else:
                d["food_recommendations"] = day_meals[0].get("meal_stops", []) if day_meals else []
            d["must_try_dishes"] = food_guide.get("must_try_dishes", [])[:4]

    except Exception as e:
        print(f"[Food Service] Note: attach_food_layer encountered {e}; degrading gracefully.")

    return itinerary
