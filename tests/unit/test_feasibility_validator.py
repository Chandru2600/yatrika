"""Standalone Rule 0 & Rule 7 tests for the deterministic feasibility validator."""

from backend.services.itinerary.feasibility_validator import validate_trip_feasibility, repair_and_validate_timeline


def _base_valid_timeline():
    return {
        "source": "Pune",
        "destination": "Coorg",
        "dates_label": "2026-11-28 to 2026-11-30",
        "claimed_sight_count": 2,
        "transit": {"mode": "train", "available": True, "distance_km": 938.8, "duration_mins": 1164},
        "budget": {
            "stay_group": 22530,
            "transit_group": 5980,
            "entry_group": 500,
            "food_group": 3600,
            "misc_group": 1000,
            "group_total": 33610,
        },
        "days": [
            {
                "day": 1,
                "date": "2026-11-28",
                "events": [
                    {"type": "travel", "mode": "train", "distance_km": 938.8, "distance_label": "home → hotel", "duration_mins": 1164, "start_time": "06:00", "end_time": "25:24", "title": "Train: Pune -> Coorg"},
                ],
            },
            {
                "day": 2,
                "date": "2026-11-29",
                "events": [
                    {"type": "travel", "mode": "car", "distance_km": 26.0, "distance_label": "hotel → sight", "duration_mins": 49, "start_time": "08:30", "end_time": "09:19", "title": "Drive"},
                    {"type": "attraction", "duration_mins": 360, "start_time": "09:19", "end_time": "15:19", "title": "Tadiyandmol Peak View Point"},
                    {"type": "attraction", "duration_mins": 60, "start_time": "17:00", "end_time": "18:00", "title": "Raja's Seat Sunset Point"},
                ],
            },
            {
                "day": 3,
                "date": "2026-11-30",
                "events": [
                    {"type": "travel", "mode": "train", "distance_km": 0.0, "duration_mins": 30, "start_time": "20:00", "end_time": "20:30", "title": "Departure Prep / Boarding Buffer"},
                    {"type": "travel", "mode": "train", "distance_km": 938.8, "distance_label": "hotel → home", "duration_mins": 1164, "start_time": "20:30", "end_time": "39:54", "title": "Return to Pune"},
                ],
            },
        ],
    }


def test_valid_timeline_passes_with_10():
    res = validate_trip_feasibility(_base_valid_timeline())
    assert res["passed"] is True
    assert res["score"] == 10.0


def test_rejects_impossible_speed_and_ghat_speed():
    tl = _base_valid_timeline()
    tl["days"][0]["events"][0]["duration_mins"] = 270  # 938.8 km in 4h30m = 208.6 km/h
    tl["days"][1]["events"][0]["distance_km"] = 73.6
    tl["days"][1]["events"][0]["duration_mins"] = 66    # 66.9 km/h on Coorg ghats
    res = validate_trip_feasibility(tl)
    assert res["passed"] is False
    speed_chk = next(c for c in res["checks"] if c["name"] == "speed_sanity")
    assert speed_chk["passed"] is False
    assert len(speed_chk["details"]["failures"]) == 2


def test_rejects_budget_mismatch_and_zero_transit():
    tl = _base_valid_timeline()
    tl["budget"]["transit_group"] = 0
    tl["budget"]["group_total"] = 70000
    res = validate_trip_feasibility(tl)
    assert res["passed"] is False
    b_chk = next(c for c in res["checks"] if c["name"] == "budget_reconciliation")
    assert b_chk["passed"] is False


def test_rejects_generic_sight_duplicates_and_short_trek():
    tl = _base_valid_timeline()
    tl["days"][1]["events"][1]["duration_mins"] = 60  # 1h Tadiandamol trek
    tl["days"][1]["events"].append({"type": "attraction", "duration_mins": 90, "start_time": "18:05", "end_time": "19:35", "title": "Hanging Bridge"})
    tl["days"][1]["events"].append({"type": "attraction", "duration_mins": 60, "start_time": "19:40", "end_time": "20:40", "title": "Raja's Seat Sunset Point"})
    res = validate_trip_feasibility(tl)
    assert res["passed"] is False
    assert any(not c["passed"] and c["name"] == "sight_integrity" for c in res["checks"])
    assert any(not c["passed"] and c["name"] == "trek_durations" for c in res["checks"])


def test_rejects_friday_taj_mahal_early_sunset_and_bad_airport_buffer():
    tl = _base_valid_timeline()
    tl["destination"] = "Agra"
    tl["dates_label"] = "2026-11-27 to 2026-11-29"
    tl["days"][0]["date"] = "2026-11-27"  # Friday
    tl["days"][0]["events"].append({"type": "attraction", "duration_mins": 120, "start_time": "08:30", "end_time": "10:30", "title": "Taj Mahal"})
    tl["days"][1]["events"][2]["start_time"] = "08:38"
    tl["days"][1]["events"][2]["end_time"] = "09:38"
    tl["days"][2]["events"][0]["title"] = "Airport Check-in & Security Buffer"
    res = validate_trip_feasibility(tl)
    assert res["passed"] is False
    names = {c["name"] for c in res["errors"]}
    assert "dates_and_opening_windows" in names
    assert "no_overlaps" in names
    assert "return_leg" in names


def test_self_correction_repairs_broken_timeline_to_pass():
    tl = _base_valid_timeline()
    tl["days"][0]["events"][0]["duration_mins"] = 270  # impossible 209 km/h speed
    tl["days"][1]["events"][1]["duration_mins"] = 60   # short 1h trek
    tl["days"][1]["events"].append({"type": "attraction", "duration_mins": 90, "start_time": "18:05", "end_time": "19:35", "title": "Hanging Bridge"})
    tl["days"][2]["events"][0]["title"] = "Airport Check-in & Security Buffer"
    tl["budget"]["group_total"] = 70000

    repaired = repair_and_validate_timeline(tl)
    assert repaired["auto_repaired"] is True
    assert len(repaired["repair_actions"]) >= 4
    assert repaired["passed"] is True
    assert repaired["score"] == 10.0
