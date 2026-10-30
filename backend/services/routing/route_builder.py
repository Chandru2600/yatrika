"""
Yatrika Travel Agent - Day Route Builder
Assembles multi-stop daily sightseeing circuits anchored to Base Camp:
Base Camp ➔ POI 1 ➔ POI 2 ➔ POI 3 ➔ Base Camp

Features:
- Queries OSRMClient for real turn-by-turn road geometry, distances, and drive times
- Graceful haversine fallback (with 1.3x road winding factor & 35 km/h average speed) if OSRM is unreachable
- Enriches legs with from/to landmark names and coordinates
- Exposes structured day routes for MapLibre map rendering and turn-by-turn timeline cards
"""

import math
import logging
from typing import List, Tuple, Dict, Any, Optional
from backend.services.routing.osrm_client import (
    OSRMClient,
    get_osrm_client,
    format_duration_str
)

logger = logging.getLogger(__name__)


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates great-circle distance between two decimal coordinates in km."""
    R = 6371.0  # Earth radius in kilometers
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (math.sin(delta_phi / 2.0) ** 2 +
         math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2)
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c


def _extract_coord(obj: Any) -> Optional[Tuple[float, float, str]]:
    """
    Extracts (latitude, longitude, name) from various POI/stay representations.
    Returns None if valid coordinates cannot be extracted.
    """
    if not obj:
        return None

    if isinstance(obj, (tuple, list)) and len(obj) >= 2:
        try:
            lat = float(obj[0])
            lon = float(obj[1])
            name = str(obj[2]) if len(obj) > 2 else "Stop"
            if -90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0:
                return (lat, lon, name)
        except (ValueError, TypeError):
            return None

    if isinstance(obj, dict):
        lat = obj.get("lat", obj.get("latitude"))
        lon = obj.get("lon", obj.get("longitude"))
        name = (obj.get("name") or obj.get("place") or
                obj.get("title") or obj.get("activity") or "Sightseeing Stop")
        try:
            lat_f = float(lat)
            lon_f = float(lon)
            if -90.0 <= lat_f <= 90.0 and -180.0 <= lon_f <= 180.0 and not (lat_f == 0.0 and lon_f == 0.0):
                return (lat_f, lon_f, str(name).strip())
        except (ValueError, TypeError):
            return None

    return None


def _build_haversine_fallback_route(
    stops: List[Tuple[float, float, str]]
) -> Dict[str, Any]:
    """
    Generates deterministic fallback route using haversine distance with
    a 1.3x road winding factor and realistic 35 km/h average driving speed.
    """
    total_km = 0.0
    total_sec = 0.0
    legs = []
    coordinates = []

    for idx, (lat, lon, name) in enumerate(stops):
        coordinates.append([round(lon, 6), round(lat, 6)])

    for idx in range(len(stops) - 1):
        from_lat, from_lon, from_name = stops[idx]
        to_lat, to_lon, to_name = stops[idx + 1]

        straight_dist = haversine_distance_km(from_lat, from_lon, to_lat, to_lon)
        # Apply 1.3x circuity factor for Indian roads/terrain
        leg_km = round(max(0.5, straight_dist * 1.3), 1)
        # 35 km/h average road speed
        drive_mins = max(5, round((leg_km / 35.0) * 60))
        leg_sec = drive_mins * 60

        total_km += leg_km
        total_sec += leg_sec

        legs.append({
            "leg_index": idx,
            "from_name": from_name,
            "to_name": to_name,
            "from_coords": [from_lat, from_lon],
            "to_coords": [to_lat, to_lon],
            "distance_meters": round(leg_km * 1000.0),
            "distance_km": leg_km,
            "duration_seconds": leg_sec,
            "duration_minutes": drive_mins,
            "duration_str": format_duration_str(leg_sec),
            "summary": f"{from_name} to {to_name}",
            "source": "haversine",
            "steps": [
                {
                    "instruction": f"Depart {from_name} and drive toward {to_name}",
                    "distance_m": round(leg_km * 1000.0),
                    "duration_s": leg_sec,
                    "name": f"{from_name} ➔ {to_name}",
                    "modifier": "straight",
                    "type": "depart"
                },
                {
                    "instruction": f"Arrive at {to_name}",
                    "distance_m": 0,
                    "duration_s": 0,
                    "name": to_name,
                    "modifier": "",
                    "type": "arrive"
                }
            ]
        })

    return {
        "source": "haversine",
        "total_distance_meters": round(total_km * 1000.0),
        "total_distance_km": round(total_km, 1),
        "total_duration_seconds": round(total_sec),
        "total_duration_minutes": max(1, round(total_sec / 60.0)),
        "total_duration_str": format_duration_str(total_sec),
        "geometry": {
            "type": "LineString",
            "coordinates": coordinates
        },
        "legs": legs
    }


def build_day_route(
    stay_coords: Any,
    poi_coords_in_order: List[Any],
    osrm_client: Optional[OSRMClient] = None
) -> Dict[str, Any]:
    """
    Chains base camp stay ➔ POIs in order ➔ base camp stay.
    Queries OSRM for real road geometry and turn-by-turn steps.
    Falls back gracefully to haversine estimates if OSRM is unavailable or fails.

    Args:
        stay_coords: (lat, lon) or dict with latitude/longitude/name of Base Camp
        poi_coords_in_order: list of POIs (lat/lon or dicts) visited during the day
        osrm_client: optional OSRMClient instance

    Returns:
        Structured day route dictionary containing:
        - source: 'osrm' or 'haversine'
        - total_distance_km
        - total_duration_minutes
        - total_duration_str
        - geometry: GeoJSON LineString
        - legs: list of leg dicts with from/to names, distance, drive time, and steps
    """
    stay_parsed = _extract_coord(stay_coords)
    if not stay_parsed:
        # Fallback to Coorg coordinates if stay is somehow empty
        stay_parsed = (12.4244, 75.7382, "Base Camp Lodging")

    stay_lat, stay_lon, stay_name = stay_parsed

    # Extract all valid POI coordinates
    stops: List[Tuple[float, float, str]] = [(stay_lat, stay_lon, stay_name)]
    for poi in poi_coords_in_order:
        p = _extract_coord(poi)
        if p:
            stops.append(p)

    # If only base camp, add a nearby exploration loop
    if len(stops) == 1:
        stops.append((stay_lat + 0.015, stay_lon + 0.012, f"Scenic {stay_name} Trail"))

    # Return loop to base camp
    stops.append((stay_lat, stay_lon, f"Return to {stay_name}"))

    # Prepare waypoints for OSRM: (longitude, latitude)
    osrm_waypoints = [(lon, lat) for lat, lon, _ in stops]

    client = osrm_client or get_osrm_client()
    osrm_result = client.get_route(osrm_waypoints, profile="driving", overview="full", steps=True)

    if osrm_result and osrm_result.get("legs"):
        # Augment OSRM legs with landmark names and coordinate pairs
        parsed_legs = osrm_result.get("legs", [])
        for idx in range(min(len(parsed_legs), len(stops) - 1)):
            leg = parsed_legs[idx]
            from_lat, from_lon, from_name = stops[idx]
            to_lat, to_lon, to_name = stops[idx + 1]

            leg["from_name"] = from_name
            leg["to_name"] = to_name
            leg["from_coords"] = [from_lat, from_lon]
            leg["to_coords"] = [to_lat, to_lon]
            leg["source"] = "osrm"

        osrm_result["source"] = "osrm"
        return osrm_result

    # If OSRM failed or returned None, use resilient haversine fallback
    return _build_haversine_fallback_route(stops)


def build_multiday_routes(
    stay_info: Dict[str, Any],
    days_list: List[Dict[str, Any]],
    osrm_client: Optional[OSRMClient] = None
) -> List[Dict[str, Any]]:
    """
    Builds day routes for all days in an itinerary.
    Returns a list of day route objects with day number and source attribution.
    """
    day_routes = []
    client = osrm_client or get_osrm_client()

    for idx, day_dict in enumerate(days_list):
        day_num = int(day_dict.get("day_number", day_dict.get("day", idx + 1)))

        # Extract POIs from morning, afternoon, evening slots
        day_pois = []
        for slot_key in ("morning", "afternoon", "evening"):
            slot_data = day_dict.get(slot_key)
            if slot_data and isinstance(slot_data, dict):
                # Check places list or direct slot attributes
                places = slot_data.get("places")
                if isinstance(places, list) and places:
                    for pl in places:
                        if isinstance(pl, dict):
                            day_pois.append(pl)
                else:
                    day_pois.append(slot_data)

        route = build_day_route(stay_info, day_pois, osrm_client=client)
        route["day"] = day_num
        route["day_number"] = day_num
        day_routes.append(route)

    return day_routes
