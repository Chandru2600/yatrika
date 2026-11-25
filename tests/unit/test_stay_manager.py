"""
Unit Tests for Stay Manager Service, IBM Granite AI + Agent 4 Fallback,
Strict Deduplication, and Exact Place Image Resolution.
"""

import pytest
from unittest.mock import patch, MagicMock
from app import create_app
from backend.services.stay.stay_service import find_managed_stays, get_stay_by_id
from backend.services.wikipedia.wiki_places_service import get_real_place_data, batch_get_real_places


@pytest.fixture
def app_client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


class TestStayManagerService:
    """Test suite for Stay Manager discovery and fallback mechanisms."""

    def test_find_managed_stays_fallback_path(self):
        """When IBM Granite is not configured, Agent 4 fallback executes successfully."""
        with patch("backend.services.stay.stay_service.is_ibm_configured", return_value=False):
            res = find_managed_stays(
                source="Bengaluru",
                destination="Coorg",
                checkin="2026-12-01",
                checkout="2026-12-03",
                budget=3000,
                travelers=2,
                purpose="all"
            )

            assert res["status"] == "success"
            assert res["source_engine"] == "agent4_fallback"
            assert len(res["stays"]) >= 2
            assert res["destination"] == "Coorg"
            assert res["nights"] == 2

            # Verify card contract
            first = res["stays"][0]
            assert "name" in first
            assert "price_per_night" in first
            assert "total_price" in first
            assert first["total_price"] == first["price_per_night"] * 2
            assert "distance_km" in first
            assert "drive_mins" in first
            assert "lat" in first and "lon" in first
            assert "img" in first
            assert "booking_links" in first
            assert "agoda" in first["booking_links"]
            assert "booking_com" in first["booking_links"]

    def test_zero_duplicate_stays_guarantee(self):
        """Verify strict deduplication guarantees no duplicate hotel names or coordinates."""
        with patch("backend.services.stay.stay_service.is_ibm_configured", return_value=False):
            res = find_managed_stays(
                source="Bengaluru",
                destination="Coorg",
                budget=2500,
                travelers=2
            )
            stays = res["stays"]
            names = [s["name"].lower() for s in stays]
            norm_names = [s["norm_name"] for s in stays]

            # All normalized names must be unique
            assert len(norm_names) == len(set(norm_names)), "Duplicate hotel detected in stays list"
            assert len(names) == len(set(names)), "Duplicate raw hotel name detected"

    def test_exact_office_location_and_days_calculation(self):
        """Testing exact office destination inside city with days and total calculation."""
        res = find_managed_stays(
            source="Bengaluru",
            destination="Infosys Electronic City, Bengaluru",
            budget=2800,
            travelers=2,
            num_days=4
        )
        assert res["status"] == "success"
        assert res["days"] == 4
        assert res["nights"] == 3
        assert len(res["stays"]) > 0
        # Check that dest_coords are resolved to Electronic City corridor
        assert 12.80 <= res["dest_coords"]["lat"] <= 12.87
        assert 77.65 <= res["dest_coords"]["lon"] <= 77.70
        # Check total price calculation
        stay = res["stays"][0]
        assert stay["nights"] == 3
        assert stay["total_price"] == stay["price_per_night"] * 3

    def test_ibm_granite_path_when_configured(self):
        """When IBM Granite is available and responds with valid JSON array, it is used."""
        mock_granite_output = """[
            {
                "name": "Coorg Pine Wood Residency",
                "type": "Boutique Homestay",
                "price_per_night": 2400,
                "rating": 4.7,
                "reviews_count": 210,
                "address": "Madikeri Town, Coorg",
                "distance_km": 1.2,
                "lat": 12.4244,
                "lon": 75.7382,
                "amenities": ["Free WiFi", "Mountain Balcony", "Breakfast"]
            },
            {
                "name": "Misty Hills Valley Resort",
                "type": "Resort",
                "price_per_night": 3600,
                "rating": 4.8,
                "reviews_count": 340,
                "address": "Siddapur Road, Coorg",
                "distance_km": 4.5,
                "lat": 12.3380,
                "lon": 75.8070,
                "amenities": ["Swimming Pool", "Spa", "Coffee Walk"]
            }
        ]"""
        with patch("backend.services.stay.stay_service.is_ibm_configured", return_value=True):
            with patch("backend.services.stay.stay_service.call_granite", return_value=mock_granite_output):
                res = find_managed_stays(
                    source="Bengaluru",
                    destination="Coorg",
                    budget=3000,
                    travelers=2
                )
                assert res["source_engine"] == "ibm_granite"
                assert len(res["stays"]) >= 2
                assert res["stays"][0]["name"] == "Coorg Pine Wood Residency"
                assert res["stays"][0]["price_per_night"] == 2400


class TestStayManagerEndpoints:
    """Test suite for Stay Manager HTTP routes."""

    def test_stay_manager_search_entry_view(self, app_client):
        """GET /stay-manager with no destination renders the clean Launchpad entry card with Continue."""
        resp = app_client.get("/stay-manager")
        assert resp.status_code == 200
        html = resp.get_data(as_text=True)
        assert "Continue to Stays" in html or "Continue" in html
        assert "tripSource" in html
        assert "tripDestination" in html
        assert "tripDays" in html

    def test_stay_manager_html_view(self, app_client):
        """GET /stay-manager with destination renders the dedicated results page."""
        resp = app_client.get("/stay-manager?destination=Coorg&source=Bengaluru")
        assert resp.status_code == 200
        html = resp.get_data(as_text=True)
        assert "Stay Manager" in html
        assert "stayMap" in html
        assert "View on Map" in html
        assert "Book" in html

    def test_stay_manager_results_endpoint(self, app_client):
        """GET /stay-manager/results renders the cards grid with facilities filters and floating map."""
        resp = app_client.get("/stay-manager/results?destination=Electronic+City+Bengaluru&source=Bengaluru&num_days=3")
        assert resp.status_code == 200
        html = resp.get_data(as_text=True)
        assert "Stays Near" in html
        assert "FACILITIES" in html
        assert "floatingMapModal" in html
        assert "View on Map" in html

    def test_stay_manager_api_search(self, app_client):
        """GET /stay-manager/api/search returns valid JSON stays."""
        resp = app_client.get("/stay-manager/api/search?destination=Coorg&source=Bengaluru&budget=2500")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "success"
        assert len(data["stays"]) > 0
        assert data["stays"][0]["lat"] is not None

    def test_stay_manager_api_route(self, app_client):
        """POST /stay-manager/api/route returns OSRM road geometry or fallback."""
        resp = app_client.post("/stay-manager/api/route", json={
            "stay_lat": 12.3375,
            "stay_lon": 75.8069,
            "dest_lat": 12.4244,
            "dest_lon": 75.7382
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert "geometry" in data
        assert data["distance_km"] > 0


class TestExactPlaceImages:
    """Test suite for verified attraction image resolution."""

    def test_curated_landmark_image_exact_match(self):
        """Iconic attractions resolve to verified authentic photographs."""
        res = get_real_place_data("Abbey Falls", "Coorg", 12.4542, 75.7175)
        assert res["img"] is not None
        assert "Abbey_Falls" in res["img"] or "Abbi_falls" in res["img"]

        res2 = get_real_place_data("Namdroling Monastery", "Coorg", 12.4286, 75.9667)
        assert res2["img"] is not None
        assert "Golden_Temple" in res2["img"] or "Monastery" in res2["img"]

    def test_batch_get_real_places_attaches_coordinates(self):
        """Batch image resolver attaches authentic photos using coordinates."""
        items = [
            ("Abbey Falls", "Coorg", 12.4542, 75.7175),
            ("Raja's Seat", "Coorg", 12.4215, 75.7364)
        ]
        results = batch_get_real_places(items)
        assert ("Abbey Falls", "Coorg") in results
        assert ("Raja's Seat", "Coorg") in results
        assert results[("Abbey Falls", "Coorg")]["img"] is not None
        assert results[("Raja's Seat", "Coorg")]["img"] is not None


class TestV3AuditRegressions:
    """Regression suite for v3 audit fixes: no fake PNRs, distance-gated flights, days consistency, budget flags."""

    def test_no_fake_pnr_or_verified_claims_on_stay_summary(self, app_client):
        resp = app_client.get(
            "/stay-manager/summary?destination=Infosys+Electronic+City,+Bengaluru&source=Bengaluru"
            "&num_days=3&travelers=2&stay_name=Test+Stay&stay_price=2400&stay_pppd=1200"
            "&transit_mode=bus&transit_title=City+Shuttle&transit_fare=120"
        )
        assert resp.status_code == 200
        html = resp.data.decode("utf-8")
        assert "YTR-" not in html
        assert "IRCTC / RTC VERIFIED" not in html
        assert "VERIFIED PASS" not in html
        assert "CONFIRMED STAY" not in html
        assert "Per-Person Total:" in html
        assert "Group Total (2 guests):" in html

    def test_no_intra_city_or_short_distance_flight(self):
        from backend.services.transit.flight_api import fetch_flight_fares
        res = fetch_flight_fares("Bengaluru", "Electronic City", dist_km=25.0, travelers=2)
        assert res["available"] is False
        assert res["schedules"] == []

    def test_stay_manager_days_match_checkin_checkout(self):
        with patch("backend.services.stay.stay_service.is_ibm_configured", return_value=False):
            res = find_managed_stays(
                source="Bengaluru",
                destination="Coorg",
                checkin="2026-11-27",
                checkout="2026-11-30",
                budget=2500,
                travelers=2,
                num_days=3
            )
            assert res["days"] == 3
            assert res["nights"] == 3

    def test_stay_manager_over_budget_flag_and_clean_address(self):
        mock_stays = [
            {
                "name": "Luxury Stay",
                "price_per_night": 6000,
                "address": "Prestige ShantiniketanWhitefieldBangalore 560048",
                "lat": 12.8452,
                "lon": 77.6602,
            }
        ]
        with patch("backend.services.stay.stay_service.is_ibm_configured", return_value=True), \
             patch("backend.services.stay.stay_service._query_ibm_granite_for_stays", return_value=mock_stays):
            res = find_managed_stays(
                source="Bengaluru",
                destination="Infosys Electronic City, Bengaluru",
                budget=2500,
                travelers=2
            )
            stay = res["stays"][0]
            assert stay["over_budget"] is True
            assert "Whitefield, Bangalore" in stay["address"]
