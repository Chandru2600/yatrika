"""
Agent 1: Geospatial & Transit Model
Calculates door-to-door transit to Base Camp Stay, road distance matrices, and driving geometry.
"""

import math
from backend.services.transit.location_resolver import resolve_location_hubs
from backend.services.transit.transit_service import calculate_intercity_transit


class GeospatialTransitModel:
    """Agent 1: Geospatial & Multimodal Transit Engine."""

    def __init__(self, osrm_url: str = "http://router.project-osrm.org"):
        self.osrm_url = osrm_url

    def calculate_door_to_door_transit(self, source: str, destination: str, stay_info: dict,
                                      travelers: int = 2, selected_mode: str = "train") -> dict:
        """
        Calculates transit from source city directly to Base Camp stay entrance.
        Leverages Ixigo multimodal engine with IRCTC trains, RTC buses, and road connectors.
        """
        transit_calc = calculate_intercity_transit(
            source=source,
            dest=destination,
            selected_mode=selected_mode,
            travelers=travelers,
            selected_class="standard",
            total_budget=25000,
            travel_style="adventure"
        )

        chosen = transit_calc.get("chosen_details", {})
        all_modes = transit_calc.get("all_options", {})
        schedules = chosen.get("schedules") or []
        first_sched = schedules[0] if schedules else {}

        dist_km = round(float(transit_calc.get("distance_km") or chosen.get("distance_km") or 0), 1)
        dur_str = chosen.get("travel_duration") or chosen.get("flight_duration") or first_sched.get("duration") or "4h 30m"
        one_way_pp = float(
            chosen.get("fare_per_traveler")
            or chosen.get("min_fare_per_seat")
            or first_sched.get("fare_per_seat")
            or first_sched.get("price_per_seat")
            or round(float(chosen.get("total_cost") or 0) / max(1, travelers))
        )
        chosen_sched = first_sched
        # Car total_cost is per-vehicle, not per-seat
        if selected_mode.lower() == "car":
            # Prefer Sedan cab schedule if available, else chosen min_fare
            sedan_sched = next((s for s in schedules if "sedan" in (s.get("operator") or "").lower() or "sedan" in (s.get("type") or "").lower()), first_sched)
            chosen_sched = sedan_sched
            vehicle_one_way = float(sedan_sched.get("fare_per_seat") or chosen.get("total_cost") or 0)
            one_way_pp = round(vehicle_one_way / max(1, travelers))
            one_way_group = round(vehicle_one_way)
        else:
            one_way_group = round(one_way_pp * max(1, travelers))

        round_trip_group = one_way_group * 2
        round_trip_pp = round(one_way_pp * 2)

        operator_title = (
            chosen.get("train_name")
            or chosen_sched.get("train_name")
            or chosen_sched.get("operator")
            or chosen_sched.get("airline")
            or chosen.get("mode_title")
            or selected_mode.title()
        )
        train_num = chosen.get("train_number") or chosen_sched.get("train_number") or ""
        if train_num and train_num not in operator_title:
            operator_title = f"{operator_title} ({train_num})"

        return {
            "source": source.title(),
            "destination": destination.title(),
            "stay_name": stay_info.get("name", "Base Camp"),
            "stay_address": stay_info.get("address", ""),
            "selected_mode": selected_mode,
            "available": chosen.get("available", True),
            "mode_title": operator_title,
            "operator": operator_title,
            "train_number": train_num,
            "origin_station": chosen.get("origin_station") or chosen.get("departure_airport") or source.title(),
            "dest_station": chosen.get("dest_station") or chosen.get("arrival_airport") or destination.title(),
            "departure_time": chosen.get("departure_time") or first_sched.get("departure") or "06:00",
            "arrival_time": chosen.get("arrival_time") or first_sched.get("arrival") or "11:30",
            "distance_km": dist_km,
            "duration_str": dur_str,
            "fare_per_person_one_way": round(one_way_pp),
            "fare_per_person_round_trip": round_trip_pp,
            "estimated_fare_inr": round_trip_group,
            "one_way_fare_inr": one_way_group,
            "location_notice": chosen.get("location_notice", ""),
            "legs": chosen.get("multimodal_legs") or schedules[:2],
            "schedules": schedules,
            "class_tiers": chosen.get("class_tiers", []),
            "all_options": all_modes,
            "details_summary": chosen.get("details_summary", ""),
        }

    def compute_distance_km(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Haversine distance calculation in kilometers."""
        R = 6371.0
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = (math.sin(dlat / 2) ** 2 +
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return round(R * c, 1)

    def estimate_drive_minutes(self, distance_km: float, is_ghat: bool = True) -> int:
        """Estimate driving time in minutes considering mountain/ghat road factor."""
        avg_speed = 35.0 if is_ghat else 50.0
        return max(5, int(round((distance_km / avg_speed) * 60)))

    def calculate_stay_to_poi_matrix(self, stay_info: dict, poi_list: list) -> list:
        """
        Computes road distances and drive times from Base Camp stay to each sightseeing attraction.
        """
        stay_lat = stay_info.get("latitude", 12.4)
        stay_lon = stay_info.get("longitude", 75.7)

        enriched = []
        for poi in poi_list:
            poi_copy = dict(poi)
            p_lat = poi_copy.get("latitude") or poi_copy.get("Latitude") or stay_lat + 0.08
            p_lon = poi_copy.get("longitude") or poi_copy.get("Longitude") or stay_lon + 0.05
            dist = self.compute_distance_km(stay_lat, stay_lon, float(p_lat), float(p_lon))
            drive_time = self.estimate_drive_minutes(dist)

            poi_copy["distance_from_stay_km"] = dist
            poi_copy["drive_minutes_from_stay"] = drive_time
            poi_copy["stay_proximity_badge"] = f"📍 {dist} km from {stay_info.get('name', 'Stay')} (~{drive_time}m drive)"
            enriched.append(poi_copy)

        return enriched
