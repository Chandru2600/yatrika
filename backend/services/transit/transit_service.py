"""
TravelPlannerAgent - Realistic Inter-City Transit Service
Integrates authentic Indian Railway (IRCTC), State RTC (KSRTC/MSRTC), and Domestic Aviation tariff models.
Calculates route distance, travel duration, fares, schedules, and class tiers
(SL, 3A, 2A, 1A for Train; Non-AC/AC Seater/AC Sleeper for Bus; Economy/Business for Flight).
"""

import math
import requests

# Authentic Indian fuel price & highway tariff parameters
FUEL_PRICE_PER_LITER = 102.86  # Current Indian Petrol rate (INR/L)
CAR_MILEAGE_KMPL = 15.5        # Average Indian sedan/hatchback mileage
BIKE_MILEAGE_KMPL = 45.0       # Average Indian motorcycle mileage
TOLL_RATE_PER_KM = 1.25        # NHAI toll rate average (INR/km)


def estimate_distance_km(source: str, dest: str) -> float:
    """
    Estimate road distance between source and destination using Nominatim + OSRM
    or fallback heuristic calculation.
    """
    try:
        headers = {"User-Agent": "TravelPlannerAgent/1.0 (IndianTransitModule)"}
        src_res = requests.get(
            f"https://nominatim.openstreetmap.org/search?format=json&q={requests.utils.quote(source)}&limit=1",
            headers=headers, timeout=5
        ).json()
        dst_res = requests.get(
            f"https://nominatim.openstreetmap.org/search?format=json&q={requests.utils.quote(dest)}&limit=1",
            headers=headers, timeout=5
        ).json()

        if src_res and dst_res:
            s_lat, s_lon = float(src_res[0]["lat"]), float(src_res[0]["lon"])
            d_lat, d_lon = float(dst_res[0]["lat"]), float(dst_res[0]["lon"])

            # Call OSRM
            osrm_url = f"http://router.project-osrm.org/route/v1/driving/{s_lon},{s_lat};{d_lon},{d_lat}?overview=false"
            route_res = requests.get(osrm_url, timeout=5).json()

            if route_res.get("code") == "Ok" and route_res.get("routes"):
                dist_m = route_res["routes"][0]["distance"]
                return round(dist_m / 1000.0, 1)

            # Haversine fallback if OSRM route missing
            dlat = math.radians(d_lat - s_lat)
            dlon = math.radians(d_lon - s_lon)
            a = math.sin(dlat/2)**2 + math.cos(math.radians(s_lat)) * math.cos(math.radians(d_lat)) * math.sin(dlon/2)**2
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
            air_dist = 6371 * c
            return round(air_dist * 1.25, 1)  # 1.25 road winding factor
    except Exception:
        pass

    # Fallback default road distance
    return 280.0


from .railway_ai import fetch_railway_ai_fares
from .flight_api import fetch_flight_fares
from .ksrtc_api import fetch_ksrtc_bus_fares


def calculate_flight_transit(source: str, dest: str, dist_km: float, travelers: int = 1, flight_class: str = "Economy") -> dict:
    """
    Domestic Flight Fare Model integrated with Flight API & IndiGo / Air India App Pricing.
    """
    return fetch_flight_fares(source, dest, dist_km, travelers, flight_class)


def calculate_train_transit(source: str, dest: str, dist_km: float, travelers: int = 1, train_class: str = "3A") -> dict:
    """
    Authentic Indian Railways Model integrated with Railway AI & IRCTC Rail Connect App Pricing.
    """
    return fetch_railway_ai_fares(source, dest, dist_km, travelers, train_class)


def calculate_bus_transit(source: str, dest: str, dist_km: float, travelers: int = 1, bus_type: str = "AC Sleeper") -> dict:
    """
    Authentic Bus Model integrated with KSRTC Awatar App Pricing (Sarige, Rajahamsa, Airavat, Ambaari Dream Class).
    """
    return fetch_ksrtc_bus_fares(source, dest, dist_km, travelers, bus_type)



def calculate_vehicle_transit(source: str, dest: str, dist_km: float, vehicle_type: str = "car") -> dict:
    """
    Calculate Outstation Cabs (Sedan, SUV) and Self-Drive fuel/tolls breakdown.
    Outstation Cab Sedan: ₹14/km + Tolls
    Outstation Cab SUV: ₹19/km + Tolls
    Self Drive Car: Fuel (15.5 km/L @ ₹102.86/L) + Tolls (₹1.25/km)
    """
    mileage = CAR_MILEAGE_KMPL if vehicle_type.lower() == "car" else BIKE_MILEAGE_KMPL
    speed_kmh = 60.0 if vehicle_type.lower() == "car" else 50.0

    travel_hours = round(dist_km / speed_kmh, 1)
    dep_mins = 7 * 60 + 0  # Departure 07:00 AM
    arr_mins = dep_mins + int(travel_hours * 60)

    arr_h = (arr_mins // 60) % 24
    arr_m = arr_mins % 60
    arrival_time_str = f"{arr_h:02d}:{arr_m:02d}"

    fuel_liters = round(dist_km / mileage, 2)
    fuel_cost = round(fuel_liters * FUEL_PRICE_PER_LITER, 2)
    tolls = round(dist_km * TOLL_RATE_PER_KM) if vehicle_type.lower() == "car" else 0
    total_fuel_toll = round(fuel_cost + tolls)

    # Outstation Cab rates
    cab_sedan_fare = round(dist_km * 14.0 + 350 + tolls)  # Dzire / Etios
    cab_suv_fare = round(dist_km * 19.0 + 500 + tolls)    # Innova Crysta / Ertiga

    class_tiers = [
        {"code": "Self-Drive", "name": f"Self Drive ({fuel_liters}L Fuel + Tolls)", "price_per_seat": total_fuel_toll, "total": total_fuel_toll, "status": "AVAILABLE"},
        {"code": "Sedan Cab", "name": "Outstation Sedan (Dzire / Etios AC)", "price_per_seat": cab_sedan_fare, "total": cab_sedan_fare, "status": "INSTANT CONFIRM"},
        {"code": "SUV Cab", "name": "Outstation SUV (Innova Crysta AC)", "price_per_seat": cab_suv_fare, "total": cab_suv_fare, "status": "TOP COMFORT"}
    ]

    schedules = [
        {
            "operator": "Self-Drive Own Car",
            "type": "Private Driving",
            "vehicle_model": "Own Car / Rented Self-Drive",
            "departure": "Flexible (07:00 Suggested)",
            "arrival": arrival_time_str,
            "duration": f"{int(travel_hours)}h {int((travel_hours % 1) * 60)}m",
            "fare_per_seat": total_fuel_toll,
            "total": total_fuel_toll,
            "fuel_liters": fuel_liters,
            "fuel_cost": fuel_cost,
            "toll_charges": tolls,
            "details": f"Fuel: {fuel_liters}L (@ ₹102.86/L) + NHAI Tolls: ₹{tolls}"
        },
        {
            "operator": "MakeMyTrip / Savaari Outstation Sedan",
            "type": "Chauffeur Driven Dedicated Cab",
            "vehicle_model": "Maruti Dzire / Toyota Etios AC (4+1)",
            "departure": "Doorstep Pickup On-Demand",
            "arrival": arrival_time_str,
            "duration": f"{int(travel_hours)}h {int((travel_hours % 1) * 60)}m",
            "fare_per_seat": cab_sedan_fare,
            "total": cab_sedan_fare,
            "fuel_liters": fuel_liters,
            "details": "Includes Tolls, State Taxes, Driver Allowance & AC Doorstep Pickup"
        },
        {
            "operator": "Premium Intercity SUV",
            "type": "Luxury Spacious Chauffeur Driven",
            "vehicle_model": "Toyota Innova Crysta / Ertiga (6+1)",
            "departure": "Doorstep Pickup On-Demand",
            "arrival": arrival_time_str,
            "duration": f"{int(travel_hours)}h {int((travel_hours % 1) * 60)}m",
            "fare_per_seat": cab_suv_fare,
            "total": cab_suv_fare,
            "fuel_liters": fuel_liters,
            "details": "Spacious Legroom, Extra Luggage Boot, Dedicated Chauffeur & AC"
        }
    ]

    return {
        "mode": vehicle_type.lower(),
        "mode_title": f"Own Vehicle / Outstation Cabs ({source.title()} to {dest.title()})",
        "distance_km": dist_km,
        "mileage_kmpl": mileage,
        "fuel_price_per_l": FUEL_PRICE_PER_LITER,
        "fuel_needed_liters": fuel_liters,
        "fuel_cost": fuel_cost,
        "toll_charges": tolls,
        "min_fare_per_seat": total_fuel_toll,
        "departure_time": "07:00",
        "arrival_time": arrival_time_str,
        "travel_duration": f"{int(travel_hours)}h {int((travel_hours % 1) * 60)}m",
        "selected_class": "Fuel & Tolls",
        "total_cost": total_fuel_toll,
        "class_tiers": class_tiers,
        "schedules": schedules,
        "details_summary": f"Drive {dist_km} km · Fuel: {fuel_liters}L (Rs. {fuel_cost}) + Tolls: Rs. {tolls} · Arrives {arrival_time_str}"
    }


from .agent import InterCityTransitAgent

# Singleton instance of InterCityTransitAgent
transit_agent = InterCityTransitAgent()


def calculate_intercity_transit(source: str, dest: str, selected_mode: str = "car",
                                travelers: int = 1, selected_class: str = None,
                                total_budget: float = 30000.0, travel_style: str = "balanced") -> dict:
    """
    Main orchestrator function executing InterCityTransitAgent perception, reasoning & planning.
    Returns multi-criteria optimization, carbon footprint, door-to-door metrics, IBM Granite rationale,
    and Day-1 timeline auto-locking status.
    """
    dist_km = estimate_distance_km(source, dest)

    # Class defaults per mode if not specified
    if not selected_class:
        if selected_mode.lower() == "train": selected_class = "3A"
        elif selected_mode.lower() == "flight": selected_class = "Economy"
        elif selected_mode.lower() == "bus": selected_class = "AC Sleeper"
        else: selected_class = "Fuel & Tolls"

    options = {
        "flight": calculate_flight_transit(source, dest, dist_km, travelers, selected_class if selected_mode.lower() == "flight" else "Economy"),
        "train": calculate_train_transit(source, dest, dist_km, travelers, selected_class if selected_mode.lower() == "train" else "3A"),
        "bus": calculate_bus_transit(source, dest, dist_km, travelers, selected_class if selected_mode.lower() == "bus" else "AC Sleeper"),
        "car": calculate_vehicle_transit(source, dest, dist_km, "car"),
        "bike": calculate_vehicle_transit(source, dest, dist_km, "bike")
    }

    # Run Autonomous Agent Reasoning Loop
    agent_res = transit_agent.run_agent_workflow(source, dest, options, selected_mode, travelers, total_budget, travel_style)
    chosen = agent_res["chosen_details"]

    return {
        "source": source,
        "destination": dest,
        "distance_km": dist_km,
        "selected_mode": chosen["mode"],
        "selected_class": selected_class,
        "transit_cost": chosen["total_cost"],
        "arrival_time": chosen["arrival_time"],
        "agent_name": agent_res["agent_name"],
        "multi_criteria_scores": agent_res["multi_criteria_scores"],
        "ai_recommended_mode": agent_res["ai_recommended_mode"],
        "ai_tradeoff_rationale": agent_res["ai_tradeoff_rationale"],
        "timeline_lock_status": agent_res["timeline_lock_status"],
        "source_perception": agent_res["source_perception"],
        "dest_perception": agent_res["dest_perception"],
        "chosen_details": chosen,
        "all_options": options
    }

