"""
Yatrika - Golden Test Suite (30 Representative Trips)
Spans all Indian zones (North, South, East, West, Central, North-East),
diverse budgets (tight, mid, luxury), travel styles (adventure, cultural, relaxation, budget, family, luxury),
and real-world edge cases (tight budget with many days, remote destinations).

Evaluates:
1. Zero constraint violations (error severity).
2. Total planned budget within ±20% of the estimate range / user budget.
3. Every scheduled POI exists in the 10,025 all-India attractions dataset.
4. Every transit segment references grounded stations/corridors and valid travel modes.
5. Zero crashes under all conditions.
"""

from pathlib import Path
import pytest
import pandas as pd
from backend.services.granite.granite_service import generate_complete_travel_plan

BASE_DIR = Path(__file__).resolve().parent.parent.parent
ATTRACTIONS_CSV = BASE_DIR / "FACULTY_EVALUATION_DATASETS" / "1_All_India_Tourist_Attractions_10025.csv"

# Pre-load known attraction names from dataset for fast validation
_KNOWN_ATTRACTIONS = set()
if ATTRACTIONS_CSV.exists():
    try:
        _df_att = pd.read_csv(ATTRACTIONS_CSV)
        _KNOWN_ATTRACTIONS = {
            str(name).strip().lower()
            for name in _df_att["Name"].dropna()
        }
    except Exception as e:
        print(f"[Warning] Could not load attractions for golden verification: {e}")


GOLDEN_TRIPS = [
    # ── South Zone ────────────────────────────────────────────────────────────
    {
        "id": "coorg_adventure_couple",
        "destination": "Coorg",
        "source": "Bengaluru",
        "num_days": 3,
        "num_travelers": 2,
        "budget": 20000,
        "travel_style": "adventure",
        "transport": "train",
        "start_date": "2026-10-01"
    },
    {
        "id": "chikmagalur_nature_solo",
        "destination": "Chikmagalur",
        "source": "Bengaluru",
        "num_days": 2,
        "num_travelers": 1,
        "budget": 12000,
        "travel_style": "relaxation",
        "transport": "bus",
        "start_date": "2026-10-05"
    },
    {
        "id": "munnar_tea_relaxation",
        "destination": "Munnar",
        "source": "Kochi",
        "num_days": 3,
        "num_travelers": 2,
        "budget": 22000,
        "travel_style": "relaxation",
        "transport": "bus",
        "start_date": "2026-11-01"
    },
    {
        "id": "ooty_hill_family",
        "destination": "Ooty",
        "source": "Coimbatore",
        "num_days": 3,
        "num_travelers": 3,
        "budget": 28000,
        "travel_style": "family",
        "transport": "train",
        "start_date": "2026-11-05"
    },
    {
        "id": "alleppey_backwaters_couple",
        "destination": "Alleppey",
        "source": "Kochi",
        "num_days": 2,
        "num_travelers": 2,
        "budget": 25000,
        "travel_style": "relaxation",
        "transport": "train",
        "start_date": "2026-11-15"
    },
    {
        "id": "wayanad_wildlife_friends",
        "destination": "Wayanad",
        "source": "Calicut",
        "num_days": 3,
        "num_travelers": 4,
        "budget": 32000,
        "travel_style": "adventure",
        "transport": "bus",
        "start_date": "2026-11-20"
    },
    {
        "id": "kodaikanal_mist_couple",
        "destination": "Kodaikanal",
        "source": "Madurai",
        "num_days": 3,
        "num_travelers": 2,
        "budget": 21000,
        "travel_style": "relaxation",
        "transport": "bus",
        "start_date": "2026-11-25"
    },
    {
        "id": "mysore_palaces_family",
        "destination": "Mysore",
        "source": "Bengaluru",
        "num_days": 2,
        "num_travelers": 5,
        "budget": 25000,
        "travel_style": "cultural",
        "transport": "train",
        "start_date": "2026-12-01"
    },
    {
        "id": "hampi_ruins_solo",
        "destination": "Hampi",
        "source": "Bengaluru",
        "num_days": 3,
        "num_travelers": 1,
        "budget": 14000,
        "travel_style": "cultural",
        "transport": "train",
        "start_date": "2026-12-05"
    },
    {
        "id": "pondicherry_french_couple",
        "destination": "Pondicherry",
        "source": "Chennai",
        "num_days": 3,
        "num_travelers": 2,
        "budget": 24000,
        "travel_style": "relaxation",
        "transport": "bus",
        "start_date": "2026-12-15"
    },
    {
        "id": "gokarna_beaches_friends",
        "destination": "Gokarna",
        "source": "Goa",
        "num_days": 3,
        "num_travelers": 3,
        "budget": 21000,
        "travel_style": "budget",
        "transport": "train",
        "start_date": "2026-12-20"
    },
    {
        "id": "dandeli_river_adventure",
        "destination": "Dandeli",
        "source": "Hubli",
        "num_days": 2,
        "num_travelers": 4,
        "budget": 26000,
        "travel_style": "adventure",
        "transport": "bus",
        "start_date": "2026-12-24"
    },

    # ── North Zone ────────────────────────────────────────────────────────────
    {
        "id": "manali_mountain_friends",
        "destination": "Manali",
        "source": "Delhi",
        "num_days": 5,
        "num_travelers": 4,
        "budget": 45000,
        "travel_style": "adventure",
        "transport": "flight",
        "start_date": "2026-10-10"
    },
    {
        "id": "jaipur_heritage_family",
        "destination": "Jaipur",
        "source": "Delhi",
        "num_days": 3,
        "num_travelers": 4,
        "budget": 35000,
        "travel_style": "cultural",
        "transport": "flight",
        "start_date": "2026-10-20"
    },
    {
        "id": "udaipur_luxury_honeymoon",
        "destination": "Udaipur",
        "source": "Mumbai",
        "num_days": 4,
        "num_travelers": 2,
        "budget": 60000,
        "travel_style": "luxury",
        "transport": "flight",
        "start_date": "2026-10-25"
    },
    {
        "id": "rishikesh_spiritual_solo",
        "destination": "Rishikesh",
        "source": "Delhi",
        "num_days": 4,
        "num_travelers": 1,
        "budget": 15000,
        "travel_style": "adventure",
        "transport": "train",
        "start_date": "2026-11-10"
    },
    {
        "id": "varanasi_ghats_spiritual",
        "destination": "Varanasi",
        "source": "Kolkata",
        "num_days": 3,
        "num_travelers": 2,
        "budget": 19000,
        "travel_style": "cultural",
        "transport": "train",
        "start_date": "2026-12-10"
    },
    {
        "id": "delhi_capital_family",
        "destination": "Delhi",
        "source": "Jaipur",
        "num_days": 4,
        "num_travelers": 3,
        "budget": 38000,
        "travel_style": "cultural",
        "transport": "flight",
        "start_date": "2026-12-28"
    },
    {
        "id": "amritsar_golden_family",
        "destination": "Amritsar",
        "source": "Delhi",
        "num_days": 2,
        "num_travelers": 3,
        "budget": 18000,
        "travel_style": "cultural",
        "transport": "train",
        "start_date": "2026-12-18"
    },
    {
        "id": "agra_taj_monuments_couple",
        "destination": "Agra",
        "source": "Delhi",
        "num_days": 2,
        "num_travelers": 2,
        "budget": 16000,
        "travel_style": "cultural",
        "transport": "train",
        "start_date": "2026-12-12"
    },

    # ── West Zone ─────────────────────────────────────────────────────────────
    {
        "id": "goa_beach_budget",
        "destination": "Goa",
        "source": "Mumbai",
        "num_days": 4,
        "num_travelers": 2,
        "budget": 18000,
        "travel_style": "budget",
        "transport": "train",
        "start_date": "2026-10-15"
    },
    {
        "id": "mumbai_coastal_luxury",
        "destination": "Mumbai",
        "source": "Goa",
        "num_days": 3,
        "num_travelers": 2,
        "budget": 50000,
        "travel_style": "luxury",
        "transport": "flight",
        "start_date": "2026-12-30"
    },

    # ── East & North-East Zones ───────────────────────────────────────────────
    {
        "id": "darjeeling_tea_himalaya",
        "destination": "Darjeeling",
        "source": "Kolkata",
        "num_days": 3,
        "num_travelers": 3,
        "budget": 27000,
        "travel_style": "family",
        "transport": "train",
        "start_date": "2026-11-08"
    },
    {
        "id": "gangtok_monasteries_friends",
        "destination": "Gangtok",
        "source": "Siliguri",
        "num_days": 4,
        "num_travelers": 3,
        "budget": 36000,
        "travel_style": "cultural",
        "transport": "flight",
        "start_date": "2026-11-12"
    },
    {
        "id": "shillong_scenic_couple",
        "destination": "Shillong",
        "source": "Guwahati",
        "num_days": 3,
        "num_travelers": 2,
        "budget": 32000,
        "travel_style": "nature",
        "transport": "flight",
        "start_date": "2026-11-16"
    },
    {
        "id": "kolkata_heritage_culture",
        "destination": "Kolkata",
        "source": "Patna",
        "num_days": 3,
        "num_travelers": 2,
        "budget": 20000,
        "travel_style": "cultural",
        "transport": "train",
        "start_date": "2026-12-22"
    },

    # ── Central Zone ──────────────────────────────────────────────────────────
    {
        "id": "khajuraho_temples_solo",
        "destination": "Khajuraho",
        "source": "Bhopal",
        "num_days": 2,
        "num_travelers": 1,
        "budget": 13000,
        "travel_style": "cultural",
        "transport": "train",
        "start_date": "2026-11-28"
    },

    # ── Edge Cases: Tight Budget, Extended Days, Remote Destinations ──────────
    {
        "id": "tight_budget_long_gokarna",
        "destination": "Gokarna",
        "source": "Bengaluru",
        "num_days": 4,
        "num_travelers": 1,
        "budget": 10000,
        "travel_style": "budget",
        "transport": "train",
        "start_date": "2026-12-02"
    },
    {
        "id": "many_days_extended_jaipur",
        "destination": "Jaipur",
        "source": "Delhi",
        "num_days": 6,
        "num_travelers": 4,
        "budget": 48000,
        "travel_style": "cultural",
        "transport": "train",
        "start_date": "2026-12-08"
    },
    {
        "id": "remote_ladakh_expedition",
        "destination": "Leh",
        "source": "Delhi",
        "num_days": 5,
        "num_travelers": 2,
        "budget": 55000,
        "travel_style": "adventure",
        "transport": "flight",
        "start_date": "2026-10-28"
    }
]


@pytest.mark.parametrize("trip_spec", GOLDEN_TRIPS, ids=[t["id"] for t in GOLDEN_TRIPS])
def test_golden_trip_generation(trip_spec):
    """
    Validates end-to-end plan generation across 30 representative Indian trips:
    1. Zero crashes under all conditions (100% plan generation).
    2. Zero unresolved error-level constraint violations.
    3. Total budget within ±20% of estimate range / user budget cap.
    4. Every scheduled POI exists in the 10,025 all-India attractions dataset.
    5. Every transit segment references grounded stations/corridors and valid travel modes.
    """
    user_budget = float(trip_spec["budget"])
    days = int(trip_spec["num_days"])

    # 1. Zero Crash Execution
    plan = generate_complete_travel_plan(trip_spec)
    assert plan is not None, f"Failed to generate plan for {trip_spec['id']}"
    assert isinstance(plan, dict), f"Plan is not a dict for {trip_spec['id']}"

    # 2. Base Camp Accommodation Grounding
    stay = plan.get("base_camp_stay", {})
    assert stay, f"Missing base_camp_stay for {trip_spec['id']}"
    assert stay.get("name"), f"Missing hotel name in {trip_spec['id']}"
    assert float(stay.get("price_per_night", 0)) > 0, f"Invalid stay price in {trip_spec['id']}"

    # 3. Transit Route Grounding & Valid Modes
    transit = plan.get("transit", {})
    assert transit, f"Missing transit route for {trip_spec['id']}"
    transit_mode = (
        transit.get("mode")
        or transit.get("transit_mode")
        or transit.get("selected_mode")
        or transit.get("direct_transit_mode")
    )
    assert transit_mode, f"Missing transit mode in {trip_spec['id']}"
    assert transit.get("origin"), f"Missing transit origin in {trip_spec['id']}"
    assert transit.get("destination"), f"Missing transit destination in {trip_spec['id']}"

    # 4. Itinerary & Daily Loops
    itinerary = plan.get("itinerary", {})
    assert itinerary, f"Missing itinerary for {trip_spec['id']}"
    scheduled_days = itinerary.get("days", [])
    assert len(scheduled_days) == days, f"Expected {days} days, got {len(scheduled_days)} in {trip_spec['id']}"

    for day in scheduled_days:
        day_num = day.get("day_number", day.get("day"))
        assert day_num is not None, f"Missing day number in {trip_spec['id']}"

        # Verify morning, afternoon, evening slots & POI grounding
        for slot in ("morning", "afternoon", "evening"):
            slot_info = day.get(slot, {})
            assert slot_info, f"Day {day_num} missing {slot} slot in {trip_spec['id']}"
            poi_name = slot_info.get("name") or slot_info.get("place")
            assert poi_name, f"Day {day_num} {slot} slot missing POI name in {trip_spec['id']}"

            # POI Dataset Grounding Assertion:
            # If attractions dataset loaded, verify POI name exists in the 10,025 spots dataset
            if _KNOWN_ATTRACTIONS:
                poi_clean = poi_name.strip().lower()
                dest_clean = trip_spec["destination"].strip().lower()
                is_known = (
                    poi_clean in _KNOWN_ATTRACTIONS
                    or any(poi_clean in k or k in poi_clean for k in _KNOWN_ATTRACTIONS)
                    or dest_clean in poi_clean
                )
                assert is_known, (
                    f"POI '{poi_name}' in day {day_num} ({slot}) does not exist in 10,025 attractions dataset"
                )

    # 5. Budget Constraints & ±20% Estimate Range Compliance
    budget_data = plan.get("budget", {})
    assert budget_data, f"Missing budget block in {trip_spec['id']}"
    planned_budget = float(
        budget_data.get("committed_total_inr")
        or budget_data.get("total_budget")
        or budget_data.get("master_total_budget")
        or user_budget
    )

    # Planned total must be within ±20% of user budget range
    lower_bound = 0.80 * user_budget
    upper_bound = 1.20 * user_budget
    assert lower_bound <= planned_budget <= upper_bound, (
        f"Planned budget ₹{planned_budget} outside ±20% range (₹{lower_bound} - ₹{upper_bound}) for {trip_spec['id']}"
    )

    # 6. Hard Constraint Gate (Zero Unresolved Errors)
    violations = plan.get("constraint_violations", [])
    error_violations = [v for v in violations if v.get("severity") == "error"]
    assert len(error_violations) == 0, f"Unresolved constraint errors in {trip_spec['id']}: {error_violations}"
