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


def test_pan_india_geospatial_hub_resolver():
    from backend.services.transit.location_resolver import resolve_location_hubs
    halebidu = resolve_location_hubs("Halebidu")
    assert halebidu["nearest_airport_code"] in ("MYQ", "IXE", "BLR")
    assert halebidu["nearest_station_code"] in ("MYS", "SBC", "MAJN")

    kasauli = resolve_location_hubs("Kasauli")
    assert kasauli["nearest_airport_code"] in ("IXC", "DED")
    assert kasauli["nearest_station_code"] != "KASA"

    aizawl = resolve_location_hubs("Aizawl")
    assert aizawl["nearest_airport_code"] in ("IXS", "IXA", "IMF", "GAU")
    assert aizawl["nearest_station_code"] != "AIZA"


def test_varanasi_train_and_no_12080_fallback():
    rail = calculate_intercity_transit("Bengaluru", "Varanasi", "train", 2)["chosen_details"]
    assert rail["train_number"] == "22687"
    assert "46h" in rail["schedules"][0]["duration"]
    assert rail["train_number"] != "12080"

    unmapped = calculate_intercity_transit("Bengaluru", "Guwahati", "train", 2)["chosen_details"]
    assert unmapped["train_number"] != "12080"


def test_agra_long_bus_private_operator_and_no_impossible_transit_days():
    from backend.services.itinerary.timeline_builder import build_timeline
    bus = calculate_intercity_transit("Bengaluru", "Agra", "bus", 2)["chosen_details"]
    assert "UPSRTC" not in bus["operator"]

    tl = build_timeline({
        "source": "Bengaluru",
        "destination": "Agra",
        "num_days": 4,
        "num_travelers": 2,
        "budget": 30000,
        "transport": "bus",
        "stay": {"name": "Maya Hotel", "price_per_night": 3000, "lat": 27.16, "lon": 78.04},
        "transit": {"mode": "bus", "title": bus["operator"], "fare_per_person": 6000, "departure": "21:30", "duration_mins": 2393, "distance_km": 1917},
        "selected_attractions": [{"id": "taj", "name": "Taj Mahal", "dur": 150, "fee": 50, "lat": 27.1751, "lon": 78.0421}],
    })
    assert "In Transit" in tl["days"][1]["events"][0]["title"]
    assert len(tl["days"][1]["sights"]) == 0
    assert len(tl["days"][0]["sights"]) == 0


def test_hampi_no_ixe_vdy_flight_and_sunset_placed_last():
    from backend.services.itinerary.timeline_builder import build_timeline
    flt = calculate_intercity_transit("Mangaluru", "Hampi", "flight", 3)["chosen_details"]
    assert flt["available"] is False

    tl = build_timeline({
        "source": "Mangaluru",
        "destination": "Hampi",
        "num_days": 1,
        "num_travelers": 3,
        "budget": 50000,
        "transport": "car",
        "stay": {"name": "Clarks Inn Hampi", "price_per_night": 3000, "lat": 15.32, "lon": 76.47},
        "transit": {"mode": "car", "title": "Sedan Cab", "fare_per_person": 1500, "departure": "06:00", "duration_mins": 350, "distance_km": 387},
        "selected_attractions": [
            {"id": "s1", "name": "Anjanadri Hills Sunset Point", "dur": 90, "fee": 0, "lat": 15.34, "lon": 76.47},
            {"id": "s2", "name": "Virupaksha Temple", "dur": 90, "fee": 0, "lat": 15.335, "lon": 76.46},
        ],
    })
    assert tl["days"][0]["sights"][-1]["name"] == "Anjanadri Hills Sunset Point"


def test_trek_duration_tiers_by_round_trip_km():
    from backend.services.itinerary.timeline_builder import build_timeline
    base = {
        "source": "Bengaluru",
        "destination": "Chikmagalur",
        "num_days": 3,
        "num_travelers": 2,
        "budget": 25000,
        "transport": "car",
        "stay": {"name": "Base Camp", "price_per_night": 2500, "lat": 13.31, "lon": 75.77},
        "transit": {"mode": "car", "title": "Sedan", "fare_per_person": 2000, "departure": "06:00", "duration_mins": 120, "distance_km": 240},
    }
    tl1 = build_timeline({**base, "selected_attractions": [{"id": "t1", "name": "Mullayanagiri Peak", "trek_km": 12, "dur": 60, "fee": 0, "lat": 13.39, "lon": 75.72}]})
    tl2 = build_timeline({**base, "selected_attractions": [{"id": "t2", "name": "Tadiandamol Peak", "trek_km": 16, "dur": 60, "fee": 0, "lat": 13.35, "lon": 75.74}]})
    tl3 = build_timeline({**base, "selected_attractions": [{"id": "t3", "name": "Kudremukh Trek", "trek_km": 22, "dur": 60, "fee": 0, "lat": 13.33, "lon": 75.75}]})
    assert [s for d in tl1["days"] for s in d["sights"]][0]["dur_mins"] == 300
    assert [s for d in tl2["days"] for s in d["sights"]][0]["dur_mins"] == 360
    assert [s for d in tl3["days"] for s in d["sights"]][0]["dur_mins"] == 450


def test_closed_days_asi_combo_checkin_buffer_and_budget_warning():
    from backend.services.itinerary.timeline_builder import build_timeline
    tl = build_timeline({
        "source": "Bengaluru",
        "destination": "Agra",
        "start_date": "2026-11-27",  # Friday
        "num_days": 2,
        "num_travelers": 2,
        "budget": 10000,
        "transport": "flight",
        "stay": {"name": "Maya Hotel", "price_per_night": 2000, "lat": 27.16, "lon": 78.04},
        "transit": {"mode": "flight", "title": "IndiGo", "fare_per_person": 4500, "departure": "06:00", "duration_mins": 160, "distance_km": 1700},
        "selected_attractions": [
            {"id": "a1", "name": "Taj Mahal", "dur": 120, "fee": 50, "lat": 27.1751, "lon": 78.0421},
            {"id": "h1", "name": "Vijaya Vittala Temple", "dur": 90, "fee": 40, "lat": 27.18, "lon": 78.02},
            {"id": "h2", "name": "Lotus Mahal Pavilion", "dur": 60, "fee": 200, "lat": 27.18, "lon": 78.03},
        ],
    })
    assert not any(s["name"] == "Taj Mahal" for s in tl["days"][0]["sights"])
    assert any(s["name"] == "Taj Mahal" for s in tl["days"][1]["sights"])
    assert tl["budget"]["entry_per_person"] == 90  # 50 (Taj) + 40 (ASI combo once)
    assert any("Airport Check-in" in ev["title"] for ev in tl["days"][-1]["events"])
    assert any("budget" in w.lower() for w in tl["warnings"])
