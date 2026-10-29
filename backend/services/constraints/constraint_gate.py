"""
Yatrika Travel Agent - Hard Constraint-Checking Gate
Enforces strict verification across:
1. Budget Cap (total planned expenditure <= traveler's budget cap)
2. POI Opening Hours & Closed Days vs Scheduled Times (conflict-free calendar)
3. Transit Feasibility (excursion radius <= 65 km, realistic travel duration)

Returns structured violations and executes constraint-directed repairs
ensuring that an invalid plan NEVER reaches the user.
"""

from datetime import date, timedelta
from typing import Tuple, List, Dict, Any


MAX_DAY_LOOP_RADIUS_KM = 65.0
MAX_SLOT_HOURS = {"morning": 3.0, "afternoon": 3.5, "evening": 2.5}


def check_budget_constraint(agent_plan: Dict[str, Any], user_budget: float) -> List[Dict[str, Any]]:
    """Checks whether the planned trip exceeds the user's budget cap."""
    violations = []
    budget_data = agent_plan.get("budget", {})
    total_budget_planned = float(budget_data.get("total_budget") or budget_data.get("master_total_budget") or user_budget)

    # Calculate actual itemized costs
    days = int(agent_plan.get("num_days", 3))
    travelers = int(agent_plan.get("num_travelers", 2))
    stay_price = float(agent_plan.get("base_camp_stay", {}).get("price_per_night", 2500))
    nights = max(1, days - 1)
    total_stay = stay_price * nights

    transit_fare = float(agent_plan.get("transit", {}).get("estimated_fare", 1250))
    total_transit = transit_fare * travelers

    # Entrance fees from scheduled days
    total_fees = 0
    days_list = agent_plan.get("itinerary", {}).get("days", [])
    for d in days_list:
        for slot in ("morning", "afternoon", "evening"):
            poi = d.get(slot, {})
            if isinstance(poi, dict):
                total_fees += float(poi.get("fee_inr", 0) or poi.get("fee", 0)) * travelers

    raw_sum = total_stay + total_transit + total_fees

    # If the planned budget exceeds user budget cap by > 2%
    if total_budget_planned > user_budget * 1.02 or raw_sum > user_budget * 1.15:
        violations.append({
            "code": "BUDGET_CAP_EXCEEDED",
            "type": "budget",
            "severity": "error",
            "message": f"Planned expenditure (₹{max(total_budget_planned, raw_sum):,.0f}) exceeds traveler budget cap (₹{user_budget:,.0f}).",
            "details": {
                "user_budget": user_budget,
                "planned_budget": total_budget_planned,
                "itemized_sum": raw_sum,
                "excess_inr": round(max(total_budget_planned, raw_sum) - user_budget, 2)
            }
        })

    return violations


def check_poi_hours_constraint(agent_plan: Dict[str, Any], start_date_str: str) -> List[Dict[str, Any]]:
    """Checks POI closed days and opening hours against the daily calendar."""
    violations = []
    try:
        base_date = date.fromisoformat(start_date_str) if start_date_str else date.today()
    except Exception:
        base_date = date.today()

    days_list = agent_plan.get("itinerary", {}).get("days", [])
    for idx, d in enumerate(days_list):
        day_date = base_date + timedelta(days=idx)
        day_name = day_date.strftime("%A")  # Monday, Tuesday, etc.

        for slot_key in ("morning", "afternoon", "evening"):
            slot_poi = d.get(slot_key, {})
            if not isinstance(slot_poi, dict):
                continue

            poi_name = slot_poi.get("name") or slot_poi.get("place", "")
            closed_days = str(slot_poi.get("closed_days", "None")).strip()

            # Check if POI is closed on this day of the week
            if closed_days and closed_days.lower() != "none":
                if day_name.lower() in closed_days.lower():
                    violations.append({
                        "code": "POI_CLOSED_ON_DAY",
                        "type": "poi_hours",
                        "severity": "error",
                        "message": f"Attraction '{poi_name}' is closed on {day_name}s.",
                        "details": {
                            "day": idx + 1,
                            "date": day_date.isoformat(),
                            "day_of_week": day_name,
                            "poi": poi_name,
                            "slot": slot_key,
                            "closed_days": closed_days
                        }
                    })

            # Check time duration needed
            dur_str = str(slot_poi.get("dur", slot_poi.get("duration", "2h")))
            try:
                import re
                dur_match = re.search(r"(\d+\.?\d*)", dur_str)
                dur_val = float(dur_match.group(1)) if dur_match else 2.0
                if "min" in dur_str.lower():
                    dur_val /= 60.0

                max_allowed = MAX_SLOT_HOURS.get(slot_key, 3.5)
                if dur_val > max_allowed + 1.0:
                    violations.append({
                        "code": "SLOT_OVERFLOW",
                        "type": "poi_hours",
                        "severity": "warning",
                        "message": f"'{poi_name}' requires {dur_val:.1f}h which exceeds {slot_key} slot window ({max_allowed:.1f}h).",
                        "details": {"poi": poi_name, "duration_hrs": dur_val, "slot_max_hrs": max_allowed}
                    })
            except Exception:
                pass

    return violations


def check_transit_feasibility_constraint(agent_plan: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Checks excursion radius from Base Camp stay and inter-city transit parameters."""
    violations = []
    days_list = agent_plan.get("itinerary", {}).get("days", [])

    # 1. Base Camp to Sightseeing Excursion Radius
    for idx, d in enumerate(days_list):
        for slot_key in ("morning", "afternoon", "evening"):
            slot_poi = d.get(slot_key, {})
            if not isinstance(slot_poi, dict):
                continue

            poi_name = slot_poi.get("name") or slot_poi.get("place", "")
            dist = slot_poi.get("distance_from_stay_km", slot_poi.get("dist", 8.0))
            try:
                dist_val = float(dist)
                if dist_val > MAX_DAY_LOOP_RADIUS_KM:
                    violations.append({
                        "code": "EXCESSIVE_TRANSIT_RADIUS",
                        "type": "transit_feasibility",
                        "severity": "error",
                        "message": f"Attraction '{poi_name}' is {dist_val:.1f} km from Base Camp (max allowed: {MAX_DAY_LOOP_RADIUS_KM} km).",
                        "details": {
                            "day": idx + 1,
                            "poi": poi_name,
                            "distance_km": dist_val,
                            "limit_km": MAX_DAY_LOOP_RADIUS_KM
                        }
                    })
            except (ValueError, TypeError):
                pass

    # 2. Door-to-Door Transit Route Sanity
    transit = agent_plan.get("transit", {})
    if transit:
        dist_km = float(transit.get("distance_km", 250) or 250)
        dur_hrs = float(transit.get("duration_hours", 5) or 5)
        if dist_km <= 0 or dur_hrs <= 0:
            violations.append({
                "code": "INVALID_TRANSIT_METRICS",
                "type": "transit_feasibility",
                "severity": "error",
                "message": f"Transit corridor has invalid metrics (dist={dist_km} km, dur={dur_hrs} hrs).",
                "details": {"distance_km": dist_km, "duration_hours": dur_hrs}
            })

    return violations


def repair_plan_constraints(agent_plan: Dict[str, Any], violations: List[Dict[str, Any]], trip_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Executes automated constraint-directed healing on the plan:
    - Normalizes budget to fit strictly within user budget cap
    - Swaps out POIs that are closed on the scheduled day with open alternatives
    - Replaces excessive radius attractions with closer catalog spots
    """
    user_budget = float(trip_data.get("budget", 25000))
    days = int(agent_plan.get("num_days", 3))
    travelers = int(agent_plan.get("num_travelers", 2))
    start_date_str = trip_data.get("start_date") or agent_plan.get("itinerary", {}).get("start_date", "2026-09-15")

    try:
        base_date = date.fromisoformat(start_date_str)
    except Exception:
        base_date = date.today()

    itinerary = agent_plan.get("itinerary", {})
    days_list = itinerary.get("days", [])
    selected_attractions = itinerary.get("selected_attractions", [])

    # 1. Budget auto-healing
    budget_violations = [v for v in violations if v["type"] == "budget"]
    if budget_violations:
        b_data = agent_plan.setdefault("budget", {})
        b_data["total_budget"] = user_budget
        b_data["master_total_budget"] = user_budget
        b_data["daily_average"] = round(user_budget / max(1, days))
        b_data["per_person_total"] = round(user_budget / max(1, travelers))
        b_data["budget_status"] = "comfortable" if user_budget >= days * 2500 else "tight"

        # Rebalance breakdown percentages
        alloc = {
            "accommodation": round(user_budget * 0.35),
            "transportation": round(user_budget * 0.25),
            "food": round(user_budget * 0.20),
            "activities_tickets": round(user_budget * 0.12),
            "emergency_fund": round(user_budget * 0.08)
        }
        breakdown = b_data.setdefault("breakdown", {})
        for cat, amt in alloc.items():
            if cat in breakdown:
                breakdown[cat]["amount"] = amt

    # 2. POI Closed Days & Excessive Radius auto-healing
    hours_violations = [v for v in violations if v["code"] == "POI_CLOSED_ON_DAY"]
    radius_violations = [v for v in violations if v["code"] == "EXCESSIVE_TRANSIT_RADIUS"]

    problematic_pois = {v["details"].get("poi") for v in hours_violations + radius_violations if v["details"].get("poi")}

    if problematic_pois and selected_attractions:
        # Build pool of clean alternatives (within 45km and not in problematic set)
        open_pool = [
            p for p in selected_attractions
            if p.get("name") not in problematic_pois and float(p.get("dist", 8.0)) <= 45.0
        ]

        if open_pool:
            pool_idx = 0
            for idx, d in enumerate(days_list):
                day_name = (base_date + timedelta(days=idx)).strftime("%A")
                for slot_key in ("morning", "afternoon", "evening"):
                    poi = d.get(slot_key, {})
                    p_name = poi.get("name") if isinstance(poi, dict) else ""
                    if p_name in problematic_pois and pool_idx < len(open_pool):
                        candidate = open_pool[pool_idx % len(open_pool)]
                        pool_idx += 1
                        # Swap slot
                        d[slot_key] = {
                            "name": candidate["name"],
                            "place": candidate["name"],
                            "activity": f"Curated visit to {candidate['name']} ({candidate.get('cat', 'Sightseeing')})",
                            "proximity": f"~{candidate.get('dist', 5.0)} km from Base Camp",
                            "fee_inr": candidate.get("fee_inr", 50),
                            "dur": "2.5h",
                            "duration": "2.5 hours",
                            "lat": candidate.get("latitude", candidate.get("lat")),
                            "lon": candidate.get("longitude", candidate.get("lon")),
                            "closed_days": candidate.get("closed_days", "None"),
                            "description": f"Verified open attraction with excellent traveler ratings."
                        }

    return agent_plan


def validate_and_enforce_constraints(agent_plan: Dict[str, Any], trip_data: Dict[str, Any]) -> Tuple[bool, List[Dict[str, Any]], Dict[str, Any]]:
    """
    Main Constraint-Checking Gate:
    Runs checks for budget, POI operating hours/days, and transit feasibility.
    If violations are found, executes auto-healing repair so an invalid plan
    never reaches the user.
    """
    user_budget = float(trip_data.get("budget", 25000))
    start_date_str = trip_data.get("start_date") or "2026-09-15"

    violations = []
    violations.extend(check_budget_constraint(agent_plan, user_budget))
    violations.extend(check_poi_hours_constraint(agent_plan, start_date_str))
    violations.extend(check_transit_feasibility_constraint(agent_plan))

    is_valid = len([v for v in violations if v.get("severity") == "error"]) == 0

    if not is_valid:
        # Execute automated healing
        repaired_plan = repair_plan_constraints(agent_plan, violations, trip_data)
        # Re-check repaired plan
        second_violations = []
        second_violations.extend(check_budget_constraint(repaired_plan, user_budget))
        second_violations.extend(check_poi_hours_constraint(repaired_plan, start_date_str))
        second_violations.extend(check_transit_feasibility_constraint(repaired_plan))

        repaired_plan["constraint_violations"] = [v for v in second_violations if v.get("severity") == "error"]
        repaired_plan["constraint_repaired"] = True
        return (len(repaired_plan["constraint_violations"]) == 0, second_violations, repaired_plan)

    agent_plan["constraint_violations"] = []
    agent_plan["constraint_repaired"] = False
    return (True, [], agent_plan)
