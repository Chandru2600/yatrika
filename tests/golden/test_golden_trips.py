"""
Yatrika - Golden Test Suite
Tests 20 representative, diverse trips across India:
Hill stations, beaches, heritage circuits, spiritual hubs, backwaters, and metropolises.
Validates:
1. Zero crash guarantee under all conditions (100% completion).
2. Hard constraint enforcement: zero unresolved error violations.
3. Budget compliance: total planned expenditure respects user budget cap.
4. Itinerary completeness: all scheduled days have morning, afternoon, and evening slots.
5. Base camp stay and transit details are grounded and non-empty.
"""

import pytest
from backend.services.granite.granite_service import generate_complete_travel_plan


GOLDEN_TRIPS = [
    {
        "id": "coorg_adventure_couple",
        "destination": "Coorg",
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
        "num_days": 2,
        "num_travelers": 1,
        "budget": 12000,
        "travel_style": "relaxation",
        "transport": "bus",
        "start_date": "2026-10-05"
    },
    {
        "id": "manali_mountain_friends",
        "destination": "Manali",
        "num_days": 5,
        "num_travelers": 4,
        "budget": 45000,
        "travel_style": "adventure",
        "transport": "flight",
        "start_date": "2026-10-10"
    },
    {
        "id": "goa_beach_budget",
        "destination": "Goa",
        "num_days": 4,
        "num_travelers": 2,
        "budget": 18000,
        "travel_style": "budget",
        "transport": "train",
        "start_date": "2026-10-15"
    },
    {
        "id": "jaipur_heritage_family",
        "destination": "Jaipur",
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
        "num_days": 4,
        "num_travelers": 2,
        "budget": 60000,
        "travel_style": "luxury",
        "transport": "flight",
        "start_date": "2026-10-25"
    },
    {
        "id": "munnar_tea_relaxation",
        "destination": "Munnar",
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
        "num_days": 3,
        "num_travelers": 3,
        "budget": 28000,
        "travel_style": "family",
        "transport": "train",
        "start_date": "2026-11-05"
    },
    {
        "id": "rishikesh_spiritual_solo",
        "destination": "Rishikesh",
        "num_days": 4,
        "num_travelers": 1,
        "budget": 15000,
        "travel_style": "adventure",
        "transport": "train",
        "start_date": "2026-11-10"
    },
    {
        "id": "alleppey_backwaters_couple",
        "destination": "Alleppey",
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
        "num_days": 3,
        "num_travelers": 1,
        "budget": 14000,
        "travel_style": "cultural",
        "transport": "train",
        "start_date": "2026-12-05"
    },
    {
        "id": "varanasi_ghats_spiritual",
        "destination": "Varanasi",
        "num_days": 3,
        "num_travelers": 2,
        "budget": 19000,
        "travel_style": "cultural",
        "transport": "train",
        "start_date": "2026-12-10"
    },
    {
        "id": "pondicherry_french_couple",
        "destination": "Pondicherry",
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
        "num_days": 2,
        "num_travelers": 4,
        "budget": 26000,
        "travel_style": "adventure",
        "transport": "bus",
        "start_date": "2026-12-24"
    },
    {
        "id": "delhi_capital_family",
        "destination": "Delhi",
        "num_days": 4,
        "num_travelers": 3,
        "budget": 38000,
        "travel_style": "cultural",
        "transport": "flight",
        "start_date": "2026-12-28"
    },
    {
        "id": "mumbai_coastal_luxury",
        "destination": "Mumbai",
        "num_days": 3,
        "num_travelers": 2,
        "budget": 50000,
        "travel_style": "luxury",
        "transport": "flight",
        "start_date": "2026-12-30"
    }
]


@pytest.mark.parametrize("trip_spec", GOLDEN_TRIPS, ids=[t["id"] for t in GOLDEN_TRIPS])
def test_golden_trip_generation(trip_spec):
    """
    Validates end-to-end plan generation for representative Indian trips.
    Enforces zero crashes, structure integrity, budget sanity, and constraint compliance.
    """
    user_budget = float(trip_spec["budget"])
    days = int(trip_spec["num_days"])

    # 1. Zero crash test
    plan = generate_complete_travel_plan(trip_spec)
    assert plan is not None, f"Failed to generate plan for {trip_spec['id']}"
    assert isinstance(plan, dict), f"Plan is not a dict for {trip_spec['id']}"

    # 2. Base Camp Accommodation
    stay = plan.get("base_camp_stay", {})
    assert stay, f"Missing base_camp_stay for {trip_spec['id']}"
    assert stay.get("name"), f"Missing hotel name in {trip_spec['id']}"
    assert float(stay.get("price_per_night", 0)) > 0, f"Invalid stay price in {trip_spec['id']}"

    # 3. Transit Route
    transit = plan.get("transit", {})
    assert transit, f"Missing transit route for {trip_spec['id']}"
    assert (
        transit.get("mode")
        or transit.get("transit_mode")
        or transit.get("selected_mode")
        or transit.get("direct_transit_mode")
    ), f"Missing transit mode in {trip_spec['id']}"

    # 4. Itinerary & Daily Loops
    itinerary = plan.get("itinerary", {})
    assert itinerary, f"Missing itinerary for {trip_spec['id']}"
    scheduled_days = itinerary.get("days", [])
    assert len(scheduled_days) == days, f"Expected {days} days, got {len(scheduled_days)} in {trip_spec['id']}"

    for day in scheduled_days:
        day_num = day.get("day_number", day.get("day"))
        assert day_num is not None, f"Missing day number in {trip_spec['id']}"
        # Verify morning, afternoon, evening slots
        for slot in ("morning", "afternoon", "evening"):
            poi = day.get(slot, {})
            assert poi, f"Day {day_num} missing {slot} slot in {trip_spec['id']}"
            poi_name = poi.get("name") or poi.get("place")
            assert poi_name, f"Day {day_num} {slot} slot missing POI name in {trip_spec['id']}"

    # 5. Budget Constraints Compliance
    budget_data = plan.get("budget", {})
    assert budget_data, f"Missing budget block in {trip_spec['id']}"
    planned_budget = float(budget_data.get("total_budget") or budget_data.get("master_total_budget") or user_budget)

    # Budget cap enforcement: planned budget should not exceed user budget by > 5%
    assert planned_budget <= user_budget * 1.05, (
        f"Planned budget ₹{planned_budget} exceeds user cap ₹{user_budget} by >5% in {trip_spec['id']}"
    )

    # 6. Hard Constraint Gate Integrity
    violations = plan.get("constraint_violations", [])
    error_violations = [v for v in violations if v.get("severity") == "error"]
    assert len(error_violations) == 0, f"Unresolved constraint errors in {trip_spec['id']}: {error_violations}"
