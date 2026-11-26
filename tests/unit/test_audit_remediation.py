"""Regression tests for Phases 1-7 remediation of the Yatrika feasibility audit."""

from backend.agents_models.cooperative_pipeline import MultiAgentCooperativePipeline
from backend.agents_models.safety_model import AccommodationsSafetyModel
from backend.agents_models.scheduling_model import ItinerarySchedulingModel
from backend.services.food.food_service import get_food_for_destination
from backend.services.stay.stay_transport_service import get_stay_transport_options
from backend.services.transit.transit_service import calculate_intercity_transit


def test_phase1_express_modes_are_distinct_and_have_return_leg():
    pipe = MultiAgentCooperativePipeline()
    base_req = {"source": "Bengaluru", "destination": "Coorg", "num_days": 3, "budget": 30000, "travel_style": "balanced", "num_travelers": 2}
    bus = pipe.run_pipeline({**base_req, "transport": "bus"})
    train = pipe.run_pipeline({**base_req, "transport": "train"})
    car = pipe.run_pipeline({**base_req, "transport": "car"})
    mys_train = pipe.run_pipeline({**base_req, "destination": "Mysuru", "transport": "train"})

    fares = {
        bus["transit"]["estimated_fare_inr"],
        train["transit"]["estimated_fare_inr"],
        car["transit"]["estimated_fare_inr"],
    }
    assert len(fares) == 3, f"Expected distinct round-trip fares across modes, got {fares}"
    assert mys_train["transit"]["distance_km"] < 170
    for plan in (bus, train, car, mys_train):
        events = [ev["title"] for d in plan["itinerary"]["timeline"]["days"] for ev in d["events"]]
        assert any("Return to" in t for t in events), "Missing return leg on final day"


def test_phase2_no_fake_evolve_back_price_and_no_suburban_rail():
    model = AccommodationsSafetyModel()
    stay = model.select_base_camp("Coorg", max_price=4000)
    assert not ("evolve back" in stay["name"].lower() and stay["price_per_night"] <= 5000)

    tr = get_stay_transport_options("Bengaluru", "Infosys Electronic City", travelers=2)
    rail_ops = [o.get("operator", "") for o in tr["all_options"].get("rail", [])]
    assert not any("suburban rail" in op.lower() for op in rail_ops)


def test_phase3_mysuru_food_and_no_null_openings():
    from app import create_app
    food = get_food_for_destination("Mysuru", 3)
    assert food["matched_level"] == "city"
    eateries = {m["eatery"] for d in food["day_meals"] for m in d["meal_stops"]}
    assert "Hotel Original Vinayaka Mylari" in eateries

    client = create_app().test_client()
    res = client.get("/planner/api/attractions/search?destination=Coorg")
    assert res.status_code == 200
    sights = res.get_json()
    assert len(sights) > 0
    assert all(s.get("opening") is not None for s in sights)


def test_phase4_no_midday_sunset_panorama():
    sched = ItinerarySchedulingModel()
    pois = [
        {"name": "Spot A", "type": "Nature", "dur": 90, "fee_inr": 0, "lat": 12.42, "lon": 75.73, "rating": 4.5},
        {"name": "Spot B", "type": "Nature", "dur": 90, "fee_inr": 0, "lat": 12.43, "lon": 75.74, "rating": 4.4},
        {"name": "Spot C", "type": "Viewpoint", "dur": 90, "fee_inr": 0, "lat": 12.44, "lon": 75.75, "rating": 4.3},
    ]
    days = sched.schedule_multiday_itinerary("Coorg", 1, {"name": "Test Stay", "latitude": 12.42, "longitude": 75.73}, pois)
    assert "Sunset Panorama" not in days[0]["evening"]["activity"]


def test_phase5_express_budget_matches_timeline_total():
    pipe = MultiAgentCooperativePipeline()
    plan = pipe.run_pipeline({"source": "Bengaluru", "destination": "Coorg", "num_days": 3, "budget": 30000, "travel_style": "balanced", "transport": "bus", "num_travelers": 2})
    assert plan["budget"]["committed_total_inr"] == plan["itinerary"]["timeline"]["budget"]["group_total"]


def test_phase6_vande_bharat_classes_and_no_blr_myq_flight():
    rail = calculate_intercity_transit("Bengaluru", "Mysuru", "train", 2)["chosen_details"]
    assert [c["code"] for c in rail["class_tiers"]] == ["CC", "EC"]
    fares_by_num = {s["train_number"]: s["fare_per_seat"] for s in rail["schedules"]}
    assert fares_by_num["16216"] != fares_by_num["12614"]

    flt = calculate_intercity_transit("Bengaluru", "Mysuru", "flight", 2)["chosen_details"]
    assert flt["available"] is False


def test_shimla_flight_routes_via_chandigarh_and_filters_junk_sights():
    from backend.services.pdf.pdf_service import generate_trip_pdf
    flt = calculate_intercity_transit("Bengaluru", "Shimla", "flight", 2)["chosen_details"]
    assert "IXC" in flt["arrival_airport"]
    assert flt["has_direct_hub"] is False

    sched = ItinerarySchedulingModel()
    sights = sched.fetch_attractions("Shimla")
    names = {s["name"].lower() for s in sights}
    for bad in ("rajiv gandhi 1944-91", "lalalajpatrai 1865-1928", "hamberg 40rp", "cave of nightmares", "a temple in my dream"):
        assert bad not in names

    pdf_path = generate_trip_pdf(
        {"id": 999, "source": "Bengaluru", "destination": "Shimla", "num_days": 4, "num_travelers": 2, "budget": 30000, "transport": "flight", "start_date": "2026-11-27", "end_date": "2026-11-30"},
        {"days": [], "selected_attractions": []},
        {"total_budget": 30000, "breakdown": {"accommodation": {"amount": 10500, "percentage": 35.0}, "transport": {"amount": 19500, "percentage": 65.0}}},
        {},
        {}
    )
    assert pdf_path and pdf_path.endswith(".pdf")
