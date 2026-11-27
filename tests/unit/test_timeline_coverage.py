"""Regression tests for Yatrika Timeline Coverage (Rules 1-7)."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from app import create_app
from backend.services.itinerary.timeline_builder import build_timeline, calculate_trip_total


def _coorg_test_trip():
    return {
        "source": "Bengaluru",
        "destination": "Coorg",
        "start_date": "",
        "end_date": "",
        "num_days": 3,
        "num_travelers": 2,
        "budget": 15000,
        "transport": "car",
        "stay": {
            "id": "hotel_caveri",
            "name": "Hotel Caveri",
            "price_per_night": 2898,
            "lat": 12.421,
            "lon": 75.738,
        },
        "transit": {
            "mode": "car",
            "title": "Sedan | MMT",
            "fare_per_person": 2232,
            "departure": "06:00 AM",
            "duration_mins": 270,
            "distance_km": 269.8,
        },
        "selected_attractions": [
            {"id": "s1", "name": "Abbi Falls", "dur": 120, "fee": 20, "lat": 12.4542, "lon": 75.7175, "dist": 6.5},
            {"id": "s2", "name": "Tadiyandmol Peak View Point", "dur": 60, "fee": 10, "lat": 12.2167, "lon": 75.6083, "dist": 35.0},
            {"id": "s3", "name": "Bylakuppe Namdroling Golden Temple", "dur": 120, "fee": 0, "lat": 12.4286, "lon": 75.9667, "dist": 34.0},
            {"id": "s4", "name": "Chelavara Falls", "dur": 120, "fee": 25, "lat": 12.2414, "lon": 75.6625, "dist": 38.0},
            {"id": "s5", "name": "Mallalli Falls", "dur": 120, "fee": 25, "lat": 12.6621, "lon": 75.7745, "dist": 48.0},
            {"id": "s6", "name": "Irupu Falls", "dur": 120, "fee": 25, "lat": 11.9664, "lon": 75.9839, "dist": 62.0},
        ],
    }


def _parse_hhmm(t: str) -> int:
    hh, mm = map(int, t.split(" ")[0].split(":"))
    extra = 24 * 60 if "(+1 day)" in t else 0
    return hh * 60 + mm + extra


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    return app.test_client()


class TestTimelineCoverage:
    def test_coorg_day1_arrival_continuous_and_day3_return(self):
        with patch("backend.services.itinerary.timeline_builder._osrm_leg", return_value=(18.0, 32)):
            tl = build_timeline(_coorg_test_trip())

        assert tl["arrival_time"] == "10:30"
        day1_events = tl["days"][0]["events"]
        # Outbound leg starts at 06:00 and arrives at 10:30; hotel event starts at 10:30 (never 08:00)
        assert day1_events[0]["start_time"] == "06:00"
        assert day1_events[0]["end_time"] == "10:30"
        assert day1_events[1]["start_time"] == "10:30"
        assert "Luggage Drop" in day1_events[1]["title"]

        # No unlabeled gap > 30 min on any day
        for day in tl["days"]:
            evs = day["events"]
            for i in range(len(evs) - 1):
                end_prev = _parse_hhmm(evs[i]["end_time"])
                start_next = _parse_hhmm(evs[i + 1]["start_time"])
                assert start_next - end_prev <= 30, f"Unlabeled gap on Day {day['day']}: {evs[i]} -> {evs[i+1]}"

        # Day 3 has check-out + return journey with real duration and after-midnight warning
        day3_last = tl["days"][2]["events"][-1]
        assert "Return to Bengaluru" in day3_last["title"]
        assert day3_last["distance_km"] == 269.8
        assert day3_last["duration_mins"] == 270
        assert day3_last["next_day_arrival"] is True
        assert any("after midnight" in w.lower() for w in tl["warnings"])

    def test_map_and_day_totals_agree_with_timeline_legs(self):
        with patch("backend.services.itinerary.timeline_builder._osrm_leg", return_value=(18.0, 32)):
            tl = build_timeline(_coorg_test_trip())

        sum_days_dist = round(sum(d["day_distance_km"] for d in tl["days"]), 1)
        sum_days_mins = sum(d["day_drive_mins"] for d in tl["days"])
        assert tl["total_distance_km"] == sum_days_dist
        assert tl["total_drive_mins"] == sum_days_mins
        for day in tl["days"]:
            leg_km = round(sum(e["distance_km"] for e in day["events"] if e["distance_label"] in ("hotel → sight", "sight → sight", "sight → hotel")), 1)
            leg_mins = sum(e["duration_mins"] for e in day["events"] if e["distance_label"] in ("hotel → sight", "sight → sight", "sight → hotel"))
            assert day["day_distance_km"] == leg_km
            assert day["day_drive_mins"] == leg_mins

    def test_entry_fees_and_grand_total_match_and_flag_over_target(self):
        totals = calculate_trip_total(_coorg_test_trip())
        assert totals["entry_per_person"] == 105
        assert totals["entry_group"] == 210
        assert totals["stay_per_person"] == 2898
        assert totals["transit_per_person"] == 2232
        assert totals["food_per_person"] == 1800
        assert totals["misc_per_person"] == 500
        assert totals["per_person_total"] == 7535
        assert totals["group_total"] == 15070
        assert totals["is_over_target"] is True
        assert totals["budget_status_label"] == "Over Target"

    def test_no_invented_dates(self):
        with patch("backend.services.itinerary.timeline_builder._osrm_leg", return_value=(15.0, 25)):
            tl = build_timeline(_coorg_test_trip())
        assert tl["dates_label"] == "Dates not set"
        assert "2026-12-02" not in json.dumps(tl)

    def test_coorg_sights_in_district_and_deduplicated(self, client):
        resp = client.get("/planner/api/attractions/search?destination=Coorg")
        assert resp.status_code == 200
        sights = resp.get_json()
        assert len(sights) > 0
        names_lower = [s["name"].lower() for s in sights]
        for bad in ("bekal", "muzhappilangad", "arakkal", "parassinikkadavu", "chembirika", "dutch fort", "karivellur", "thirunelli", "chunchanakatte"):
            assert not any(bad in n for n in names_lower), f"Out-of-district sight leaked for Coorg: {bad}"
        irupu_matches = [n for n in names_lower if "irupu" in n or "iruppu" in n]
        assert len(irupu_matches) <= 1

    def test_timeline_api_and_pdf_draft_endpoint(self, client):
        payload = _coorg_test_trip()
        with patch("backend.services.itinerary.timeline_builder._osrm_leg", return_value=(18.0, 32)):
            r1 = client.post("/planner/api/timeline/build", json=payload)
            assert r1.status_code == 200
            d1 = r1.get_json()
            assert d1["status"] == "success"
            assert d1["timeline"]["budget"]["group_total"] == 15070

            r2 = client.post("/planner/api/pdf_draft", json=payload)
            assert r2.status_code == 200
            assert r2.mimetype == "application/pdf"
            assert r2.data.startswith(b"%PDF")

    def test_wizard_js_persists_stay_transit_and_sights(self):
        js_text = Path("frontend/static/js/wizard.js").read_text(encoding="utf-8")
        for key in ("selectedStay:", "selectedAttractions:", "transitDetails:", "transitCost:"):
            assert key in js_text
