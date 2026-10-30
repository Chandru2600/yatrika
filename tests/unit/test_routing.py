"""
Unit & Golden Tests for Yatrika Routing Services:
1. OSRMClient:
   - Valid response parsing (GeoJSON geometry, total/leg distance and duration, turn-by-turn steps)
   - Failure resilience (HTTP 500, Timeout, ConnectionError, NoRoute) -> returns None
   - In-memory cache hit avoids second HTTP call
   - SQLite cache persistence and retrieval
2. RouteBuilder:
   - Fallback path with OSRM disabled / returning None (haversine road winding model)
   - Successful OSRM path with landmark name enrichment
3. Golden Routing Test:
   - 1-day Coorg itinerary produces day route with road geometry when OSRM is mocked
   - 1-day Coorg itinerary produces valid itinerary with zero crashes when OSRM is not mocked
"""

import json
from unittest.mock import patch, MagicMock
import pytest
import requests

from backend.services.routing.osrm_client import (
    OSRMClient,
    clear_osrm_memory_cache,
    format_duration_str,
    format_step_instruction
)
from backend.services.routing.route_builder import (
    build_day_route,
    build_multiday_routes,
    haversine_distance_km
)
from backend.services.granite.granite_service import generate_complete_travel_plan


SAMPLE_OSRM_OK_PAYLOAD = {
    "code": "Ok",
    "routes": [
        {
            "distance": 18500.5,
            "duration": 1560.2,
            "geometry": {
                "type": "LineString",
                "coordinates": [
                    [75.7382, 12.4244],
                    [75.7320, 12.4300],
                    [75.7200, 12.4500],
                    [75.7382, 12.4244]
                ]
            },
            "legs": [
                {
                    "distance": 8500.0,
                    "duration": 720.0,
                    "summary": "Madikeri-Abbey Falls Road",
                    "steps": [
                        {
                            "name": "Club Road",
                            "distance": 500.0,
                            "duration": 60.0,
                            "maneuver": {"type": "depart", "modifier": "right"}
                        },
                        {
                            "name": "Abbey Falls Road",
                            "distance": 8000.0,
                            "duration": 660.0,
                            "maneuver": {"type": "turn", "modifier": "left"}
                        }
                    ]
                },
                {
                    "distance": 10000.5,
                    "duration": 840.2,
                    "summary": "Madikeri Bypass",
                    "steps": [
                        {
                            "name": "Madikeri Bypass",
                            "distance": 10000.5,
                            "duration": 840.2,
                            "maneuver": {"type": "arrive", "modifier": ""}
                        }
                    ]
                }
            ]
        }
    ],
    "waypoints": [
        {"location": [75.7382, 12.4244], "name": "Base Camp"},
        {"location": [75.7200, 12.4500], "name": "Abbey Falls"},
        {"location": [75.7382, 12.4244], "name": "Base Camp"}
    ]
}


class TestOSRMClient:
    """Tests OSRMClient parsing, caching, and resilience."""

    def setup_method(self):
        clear_osrm_memory_cache()
        try:
            from backend.database.db import get_db_connection
            conn = get_db_connection()
            conn.execute("DELETE FROM osrm_cache")
            conn.commit()
            conn.close()
        except Exception:
            pass

    def test_osrm_valid_response_parsing(self):
        client = OSRMClient(base_url="https://router.project-osrm.org", timeout=5.0)
        waypoints = [(75.7382, 12.4244), (75.7200, 12.4500), (75.7382, 12.4244)]

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = SAMPLE_OSRM_OK_PAYLOAD

        with patch("requests.get", return_value=mock_resp) as mock_get:
            result = client.get_route(waypoints, profile="driving")

            assert result is not None
            assert result["source"] == "osrm"
            assert result["total_distance_km"] == pytest.approx(18.5, 0.1)
            assert result["total_duration_minutes"] == 26
            assert result["total_duration_str"] == "26m"
            assert result["geometry"]["type"] == "LineString"
            assert len(result["geometry"]["coordinates"]) == 4

            # Verify leg details and turn-by-turn steps
            legs = result["legs"]
            assert len(legs) == 2
            assert legs[0]["distance_km"] == 8.5
            assert legs[0]["duration_minutes"] == 12
            assert len(legs[0]["steps"]) == 2
            assert "Depart" in legs[0]["steps"][0]["instruction"]
            assert "Turn left" in legs[0]["steps"][1]["instruction"]

            mock_get.assert_called_once()

    def test_osrm_failure_returns_none(self):
        client = OSRMClient()
        waypoints = [(75.7382, 12.4244), (75.7200, 12.4500)]

        # 1. HTTP 500 error
        mock_500 = MagicMock()
        mock_500.status_code = 500
        with patch("requests.get", return_value=mock_500):
            assert client.get_route(waypoints) is None

        # 2. Timeout exception
        with patch("requests.get", side_effect=requests.exceptions.Timeout("Connection timed out")):
            assert client.get_route(waypoints) is None

        # 3. ConnectionError
        with patch("requests.get", side_effect=requests.exceptions.ConnectionError("Network down")):
            assert client.get_route(waypoints) is None

        # 4. Empty / malformed response code
        mock_err_code = MagicMock()
        mock_err_code.status_code = 200
        mock_err_code.json.return_value = {"code": "NoRoute", "message": "No route found"}
        with patch("requests.get", return_value=mock_err_code):
            assert client.get_route(waypoints) is None

        # 5. Invalid / insufficient waypoints
        assert client.get_route([(75.7382, 12.4244)]) is None
        assert client.get_route([]) is None

    def test_osrm_cache_hit_avoids_second_http_call(self):
        client = OSRMClient()
        waypoints = [(75.7382, 12.4244), (75.7200, 12.4500)]

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = SAMPLE_OSRM_OK_PAYLOAD

        with patch("requests.get", return_value=mock_resp) as mock_get:
            # First call -> hits HTTP endpoint
            res1 = client.get_route(waypoints)
            assert res1 is not None
            assert mock_get.call_count == 1

            # Second call -> must return from in-memory cache without HTTP call
            res2 = client.get_route(waypoints)
            assert res2 is not None
            assert mock_get.call_count == 1
            assert res1["total_distance_km"] == res2["total_distance_km"]

    def test_osrm_sqlite_cache_persistence(self):
        client = OSRMClient()
        waypoints = [(75.12345, 12.54321), (75.22345, 12.64321)]

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = SAMPLE_OSRM_OK_PAYLOAD

        with patch("requests.get", return_value=mock_resp):
            res1 = client.get_route(waypoints)
            assert res1 is not None

        # Clear in-memory cache to force SQLite read
        clear_osrm_memory_cache()

        # Mock requests to fail; client must retrieve from SQLite cache
        with patch("requests.get", side_effect=RuntimeError("Should not be called")):
            res2 = client.get_route(waypoints)
            assert res2 is not None
            assert res2["total_distance_km"] == res1["total_distance_km"]


class TestRouteBuilder:
    """Tests route building and haversine fallback."""

    def test_route_builder_fallback_with_osrm_disabled(self):
        stay_coords = {"latitude": 12.4244, "longitude": 75.7382, "name": "Coorg Base Camp"}
        poi_coords = [
            {"lat": 12.4500, "lon": 75.7200, "name": "Abbey Falls"},
            {"lat": 12.4150, "lon": 75.7400, "name": "Raja Seat"}
        ]

        # Force OSRM to return None (simulate network down or disabled)
        with patch("backend.services.routing.osrm_client.OSRMClient.get_route", return_value=None):
            day_route = build_day_route(stay_coords, poi_coords)

            assert day_route is not None
            assert day_route["source"] == "haversine"
            assert day_route["total_distance_km"] > 0
            assert day_route["total_duration_minutes"] > 0
            assert day_route["geometry"]["type"] == "LineString"
            # 3 stops + return to base camp = 4 points
            assert len(day_route["geometry"]["coordinates"]) == 4

            legs = day_route["legs"]
            assert len(legs) == 3
            assert legs[0]["from_name"] == "Coorg Base Camp"
            assert legs[0]["to_name"] == "Abbey Falls"
            assert legs[1]["from_name"] == "Abbey Falls"
            assert legs[1]["to_name"] == "Raja Seat"
            assert legs[2]["to_name"] == "Return to Coorg Base Camp"
            assert legs[0]["distance_km"] > 0
            assert legs[0]["source"] == "haversine"

    def test_route_builder_with_osrm_success(self):
        stay_coords = (12.4244, 75.7382, "Coorg Plantation Stay")
        poi_coords = [{"lat": 12.4500, "lon": 75.7200, "name": "Abbey Falls"}]

        with patch("requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = SAMPLE_OSRM_OK_PAYLOAD
            mock_get.return_value = mock_resp

            day_route = build_day_route(stay_coords, poi_coords)
            assert day_route is not None
            assert day_route["source"] == "osrm"
            assert len(day_route["legs"]) == 2
            assert day_route["legs"][0]["from_name"] == "Coorg Plantation Stay"
            assert day_route["legs"][0]["to_name"] == "Abbey Falls"


class TestGoldenRouting:
    """End-to-end golden tests for itinerary route integration."""

    def test_golden_1day_coorg_route_with_osrm_mocked(self):
        trip_spec = {
            "destination": "Coorg",
            "source": "Bengaluru",
            "num_days": 1,
            "num_travelers": 2,
            "budget": 15000,
            "travel_style": "adventure",
            "transport": "car",
            "start_date": "2026-10-10"
        }

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = SAMPLE_OSRM_OK_PAYLOAD

        with patch("requests.get", return_value=mock_resp):
            plan = generate_complete_travel_plan(trip_spec)

            assert plan is not None
            assert isinstance(plan, dict)

            itinerary = plan.get("itinerary", {})
            assert "day_routes" in itinerary, "itinerary must expose 'day_routes'"
            day_routes = itinerary["day_routes"]
            assert len(day_routes) >= 1

            d1_route = day_routes[0]
            assert d1_route["geometry"]["type"] == "LineString"
            assert len(d1_route["geometry"]["coordinates"]) > 0
            assert d1_route["total_distance_km"] > 0

            # Verify Agent 2 scheduler feedback integration
            day1 = itinerary["days"][0]
            morning = day1.get("morning", {})
            assert "transit_drive_mins" in morning
            assert "transit_distance_km" in morning
            assert "transit_source" in morning

    def test_golden_1day_coorg_route_live_or_fallback(self):
        """Zero crash guarantee: itinerary generates successfully under any network conditions."""
        trip_spec = {
            "destination": "Coorg",
            "source": "Bengaluru",
            "num_days": 1,
            "num_travelers": 2,
            "budget": 15000,
            "travel_style": "relaxation",
            "transport": "car",
            "start_date": "2026-10-15"
        }

        plan = generate_complete_travel_plan(trip_spec)
        assert plan is not None
        assert isinstance(plan, dict)

        itinerary = plan.get("itinerary", {})
        assert "day_routes" in itinerary
        day_routes = itinerary["day_routes"]
        assert len(day_routes) == 1
        assert day_routes[0]["source"] in ("osrm", "haversine")
        assert day_routes[0]["total_distance_km"] > 0
