"""
Yatrika Travel Agent - OSRM Routing Client
Interacts with the OSRM (Open Source Routing Machine) routing engine:
- Connects to public demo server or self-hosted instance (via OSRM_BASE_URL)
- Parses full route geometry (GeoJSON LineString), distance, duration, and turn-by-turn steps
- Two-tier caching: high-speed in-memory LRU-style dict + persistent SQLite table
- Strict 10s timeout, zero-crash guarantee: returns None on any failure so caller gracefully falls back
"""

import json
import logging
import requests
from typing import List, Tuple, Dict, Any, Optional
from backend.config import get_config

logger = logging.getLogger(__name__)

# In-memory session cache for repeated coordinates within the runtime
_IN_MEMORY_CACHE: Dict[str, Dict[str, Any]] = {}


def clear_osrm_memory_cache() -> None:
    """Clears the in-memory cache (primarily for unit tests)."""
    _IN_MEMORY_CACHE.clear()


def format_duration_str(seconds: float) -> str:
    """Converts seconds into human-readable duration like '1h 15m' or '24m'."""
    mins = max(1, round(seconds / 60.0))
    hours = mins // 60
    rem_mins = mins % 60
    if hours > 0:
        return f"{hours}h {rem_mins}m" if rem_mins > 0 else f"{hours}h"
    return f"{rem_mins}m"


def format_step_instruction(step: Dict[str, Any]) -> str:
    """Generates human-friendly navigational instruction from OSRM maneuver."""
    maneuver = step.get("maneuver", {})
    m_type = maneuver.get("type", "turn")
    modifier = maneuver.get("modifier", "")
    name = str(step.get("name", "")).strip()

    if m_type == "depart":
        return f"Depart on {name}" if name else "Depart from starting point"
    if m_type == "arrive":
        return f"Arrive at destination ({name})" if name else "Arrive at destination"
    if m_type in ("fork", "merge", "off ramp", "on ramp"):
        base = m_type.capitalize()
        if modifier:
            base += f" to the {modifier}"
        return f"{base} onto {name}" if name else base
    if modifier and name:
        return f"Turn {modifier} onto {name}"
    if modifier:
        return f"Turn {modifier}"
    if name:
        return f"Continue on {name}"
    return "Continue on current road"


class OSRMClient:
    """
    Client for Open Source Routing Machine (OSRM) HTTP API.
    """

    def __init__(self, base_url: Optional[str] = None, timeout: float = 10.0):
        if base_url:
            self.base_url = base_url.rstrip("/")
        else:
            try:
                cfg = get_config()
                self.base_url = getattr(cfg, "OSRM_BASE_URL", "https://router.project-osrm.org").rstrip("/")
            except Exception:
                self.base_url = "https://router.project-osrm.org"
        self.timeout = timeout

    @staticmethod
    def _make_cache_key(profile: str, waypoints: List[Tuple[float, float]]) -> str:
        """
        Creates a deterministic cache key from profile and coordinates rounded to 5 decimal places (~1m precision).
        Format: 'driving:lon1,lat1;lon2,lat2;...'
        """
        coords_str = ";".join(f"{float(lon):.5f},{float(lat):.5f}" for lon, lat in waypoints)
        return f"{profile}:{coords_str}"

    @staticmethod
    def _read_from_sqlite(cache_key: str) -> Optional[Dict[str, Any]]:
        """Reads cached parsed route from SQLite table."""
        try:
            from backend.database.db import get_db_connection
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT response_json FROM osrm_cache WHERE cache_key = ?", (cache_key,))
            row = cursor.fetchone()
            conn.close()
            if row and row["response_json"]:
                return json.loads(row["response_json"])
        except Exception as e:
            logger.debug(f"[OSRM] SQLite cache read error: {e}")
        return None

    @staticmethod
    def _write_to_sqlite(cache_key: str, data: Dict[str, Any]) -> None:
        """Writes parsed route to SQLite table."""
        try:
            from backend.database.db import get_db_connection
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO osrm_cache (cache_key, response_json, created_at)
                VALUES (?, ?, datetime('now'))
                """,
                (cache_key, json.dumps(data))
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.debug(f"[OSRM] SQLite cache write error: {e}")

    def get_route(
        self,
        waypoints: List[Tuple[float, float]],
        profile: str = "driving",
        overview: str = "full",
        steps: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Queries OSRM /route/v1/{profile}/{coordinates}
        Args:
            waypoints: list of (longitude, latitude) tuples or lists (must have at least 2 points)
            profile: OSRM profile (default 'driving')
            overview: geometry overview ('full', 'simplified', 'false')
            steps: whether to return turn-by-turn steps
        Returns:
            Structured route dictionary with GeoJSON geometry, distance, duration, and legs, or None on failure.
        """
        if not waypoints or len(waypoints) < 2:
            return None

        # Sanitize coordinate pairs
        cleaned_pts: List[Tuple[float, float]] = []
        for pt in waypoints:
            try:
                lon = float(pt[0])
                lat = float(pt[1])
                # Basic range validation
                if -180.0 <= lon <= 180.0 and -90.0 <= lat <= 90.0:
                    cleaned_pts.append((lon, lat))
                else:
                    return None
            except (ValueError, TypeError, IndexError):
                return None

        if len(cleaned_pts) < 2:
            return None

        cache_key = self._make_cache_key(profile, cleaned_pts)

        # 1. Check in-memory cache
        if cache_key in _IN_MEMORY_CACHE:
            return _IN_MEMORY_CACHE[cache_key]

        # 2. Check SQLite persistent cache
        cached_db = self._read_from_sqlite(cache_key)
        if cached_db:
            _IN_MEMORY_CACHE[cache_key] = cached_db
            return cached_db

        # 3. Call OSRM HTTP endpoint
        coords_path = ";".join(f"{lon},{lat}" for lon, lat in cleaned_pts)
        url = f"{self.base_url}/route/v1/{profile}/{coords_path}"
        params = {
            "overview": overview,
            "steps": "true" if steps else "false",
            "geometries": "geojson"
        }
        headers = {
            "User-Agent": "Yatrika-Travel-Planner/1.0 (India Itinerary Engine; contact: support@yatrika.in)"
        }

        try:
            resp = requests.get(url, params=params, headers=headers, timeout=self.timeout)
            if resp.status_code != 200:
                logger.warning(f"[OSRM] Non-200 HTTP response: {resp.status_code} for {url}")
                return None

            data = resp.json()
            if data.get("code") != "Ok" or not data.get("routes"):
                logger.warning(f"[OSRM] Service error code: {data.get('code')}")
                return None

            primary_route = data["routes"][0]
            parsed_result = self._parse_osrm_route(primary_route, cleaned_pts)
            if not parsed_result:
                return None

            # Store in caches
            _IN_MEMORY_CACHE[cache_key] = parsed_result
            self._write_to_sqlite(cache_key, parsed_result)

            return parsed_result

        except Exception as e:
            logger.warning(f"[OSRM] Request failed: {e}")
            return None

    def _parse_osrm_route(self, route: Dict[str, Any], waypoints: List[Tuple[float, float]]) -> Optional[Dict[str, Any]]:
        """Parses raw OSRM route payload into normalized Yatrika schema."""
        try:
            total_dist_m = float(route.get("distance", 0.0))
            total_dur_s = float(route.get("duration", 0.0))
            geometry = route.get("geometry")

            # Validate geometry format (must be GeoJSON LineString)
            if not isinstance(geometry, dict) or geometry.get("type") != "LineString":
                if isinstance(geometry, list):
                    geometry = {"type": "LineString", "coordinates": geometry}
                else:
                    geometry = {
                        "type": "LineString",
                        "coordinates": [[lon, lat] for lon, lat in waypoints]
                    }

            raw_legs = route.get("legs", [])
            parsed_legs = []

            for idx, leg in enumerate(raw_legs):
                leg_dist_m = float(leg.get("distance", 0.0))
                leg_dur_s = float(leg.get("duration", 0.0))
                leg_summary = str(leg.get("summary", "")).strip()

                raw_steps = leg.get("steps", [])
                parsed_steps = []
                for s in raw_steps:
                    parsed_steps.append({
                        "instruction": format_step_instruction(s),
                        "distance_m": round(float(s.get("distance", 0.0)), 1),
                        "duration_s": round(float(s.get("duration", 0.0)), 1),
                        "name": str(s.get("name", "")).strip(),
                        "modifier": s.get("maneuver", {}).get("modifier", ""),
                        "type": s.get("maneuver", {}).get("type", "")
                    })

                parsed_legs.append({
                    "leg_index": idx,
                    "distance_meters": round(leg_dist_m, 1),
                    "distance_km": round(leg_dist_m / 1000.0, 2),
                    "duration_seconds": round(leg_dur_s, 1),
                    "duration_minutes": max(1, round(leg_dur_s / 60.0)),
                    "duration_str": format_duration_str(leg_dur_s),
                    "summary": leg_summary or f"Leg {idx+1}",
                    "steps": parsed_steps
                })

            return {
                "source": "osrm",
                "total_distance_meters": round(total_dist_m, 1),
                "total_distance_km": round(total_dist_m / 1000.0, 2),
                "total_duration_seconds": round(total_dur_s, 1),
                "total_duration_minutes": max(1, round(total_dur_s / 60.0)),
                "total_duration_str": format_duration_str(total_dur_s),
                "geometry": geometry,
                "legs": parsed_legs
            }

        except Exception as e:
            logger.warning(f"[OSRM] Route parsing error: {e}")
            return None


def get_osrm_client() -> OSRMClient:
    """Returns an initialized OSRMClient instance."""
    return OSRMClient()
