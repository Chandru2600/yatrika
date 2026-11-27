"""
Cooperative 4-Agent Travel Planning Pipeline
Coordinates:
1. Agent 4: Accommodations & Safety (Stay-First Anchor)
2. Agent 1: Geospatial & Transit (Door-to-door transit to stay)
3. Agent 2: Itinerary Scheduling (Daily sightseeing loops anchored to stay)
4. Agent 3: Budget & Expense (ML Regression & financial feasibility)
"""

from backend.agents_models.safety_model import AccommodationsSafetyModel
from backend.agents_models.geospatial_model import GeospatialTransitModel
from backend.agents_models.scheduling_model import ItinerarySchedulingModel
from backend.agents_models.budget_model import BudgetExpenseModel


class MultiAgentCooperativePipeline:
    """
    Executes the Stay-First Cooperative Multi-Agent Travel Planning Pipeline.
    """

    def __init__(self):
        self.agent4_safety = AccommodationsSafetyModel()
        self.agent1_transit = GeospatialTransitModel()
        self.agent2_scheduling = ItinerarySchedulingModel()
        self.agent3_budget = BudgetExpenseModel()

    def run_pipeline(self, trip_input: dict) -> dict:
        """
        Executes end-to-end trip planning across the 4 specialized agents.
        """
        source = trip_input.get("source", "Bengaluru").strip() or "Bengaluru"
        dest = trip_input.get("destination", "Coorg").strip() or "Coorg"
        days = int(trip_input.get("num_days", 3) or 3)
        travelers = int(trip_input.get("num_travelers", 2) or 2)
        budget = float(trip_input.get("budget", 25000) or 25000)
        style = trip_input.get("travel_style", "adventure")
        transport = trip_input.get("transport", "train")
        interests = trip_input.get("interests", ["nature", "viewpoints"])
        start_date = trip_input.get("start_date", "2026-09-15")

        # ── Step 1: Agent 4 (Accommodations & Safety Model) ──────────────
        # Select Base Camp stay first (Stay-First Anchor)
        max_night_budget = (budget * 0.4) / max(1, days - 1)
        base_camp_stay = self.agent4_safety.select_base_camp(
            destination=dest,
            travel_style=style,
            max_price=max_night_budget
        )
        tiered_hotels = self.agent4_safety.get_tiered_accommodations(
            destination=dest,
            base_camp_stay=base_camp_stay,
            max_price=max_night_budget
        )

        # ── Step 2: Agent 1 (Geospatial & Transit Model) ─────────────────
        # Calculate door-to-door transit from source directly to Base Camp stay
        transit_info = self.agent1_transit.calculate_door_to_door_transit(
            source=source,
            destination=dest,
            stay_info=base_camp_stay,
            travelers=travelers,
            selected_mode=transport
        )

        approx_distance = float(transit_info.get("distance_km") or 0)
        if not approx_distance:
            legs = transit_info.get("legs", [])
            if legs:
                approx_distance = sum(float(l.get("distance_km", 0)) for l in legs)

        dur_str = transit_info.get("duration_str") or "4h 30m"
        from backend.services.itinerary.timeline_builder import _parse_duration_mins, build_timeline
        dur_mins = _parse_duration_mins(dur_str, 270)
        dur_hours = round(dur_mins / 60.0, 1)

        fare_inr = int(float(transit_info.get("estimated_fare_inr") or 0))
        one_way_pp = int(float(transit_info.get("fare_per_person_one_way") or 0))
        round_trip_pp = int(float(transit_info.get("per_person_fare_inr") or (one_way_pp * 2)))
        # Include last-mile airport/rail road transfer in door-to-door duration when destination has no direct hub
        if not transit_info.get("has_direct_hub", True):
            from backend.services.transit.location_resolver import resolve_location_hubs
            dst_hub = resolve_location_hubs(dest)
            if transport.lower() == "flight":
                dur_mins += int(round(float(dst_hub.get("airport_transfer_hours", 0)) * 60))
            elif transport.lower() == "train":
                dur_mins += int(round(float(dst_hub.get("rail_transfer_hours", 0)) * 60))
            dur_hours = round(dur_mins / 60.0, 1)
        op_title = transit_info.get("mode_title") or f"{transport.title()}"
        transit_info.update({
            "origin": source.title(),
            "destination": dest.title(),
            "estimated_fare": fare_inr,
            "direct_transit_mode": op_title,
            "distance_km": round(approx_distance, 1),
            "duration_hours": dur_hours,
            "duration_mins": dur_mins,
            "description": transit_info.get("location_notice") or (
                f"{op_title} from {transit_info.get('origin_station', source.title())} "
                f"to {transit_info.get('dest_station', dest.title())} · {round(approx_distance, 1)} km ({dur_str})."
            )
        })

        # Fetch tourist spots and compute distance matrix from Base Camp stay
        stay_coords = (base_camp_stay.get("latitude", 12.4), base_camp_stay.get("longitude", 75.7))
        raw_pois = self.agent2_scheduling.fetch_attractions(dest, interests, stay_coords=stay_coords)
        enriched_pois = self.agent1_transit.calculate_stay_to_poi_matrix(base_camp_stay, raw_pois)

        # ── Step 3: Agent 2 (Itinerary Scheduling Model) ─────────────────
        # Arrange attractions into daily loops departing and returning to Base Camp
        daily_itinerary = self.agent2_scheduling.schedule_multiday_itinerary(
            destination=dest,
            num_days=days,
            stay_info=base_camp_stay,
            enriched_pois=enriched_pois,
            travel_style=style
        )

        # ── Step 4: Budget & Expense Calculation ─────────────────────────
        transit_fare = float(transit_info.get("estimated_fare_inr") or 0)
        budget_analysis = self.agent3_budget.calculate_stay_first_budget(
            total_budget=budget,
            travelers=travelers,
            days=days,
            stay_info=base_camp_stay,
            transit_fare=transit_fare
        )

        # ── Selected Attractions List for Overview & Timeline ────────────
        selected_attractions = []
        for p in enriched_pois[:16]:
            selected_attractions.append({
                "id": p.get("id", f"att_{len(selected_attractions)+1}"),
                "name": p["name"],
                "city": p.get("city", dest.title()),
                "icon": p.get("icon", "📍"),
                "cat": p.get("cat", "Sightseeing"),
                "type": p.get("type", "Attraction"),
                "dur": p.get("dur", 90),
                "fee": p.get("fee_inr", p.get("fee", 0)),
                "dist": p.get("distance_from_stay_km", p.get("dist", 4.5)),
                "rating": p.get("rating", 4.6),
                "latitude": p.get("latitude", p.get("lat")),
                "longitude": p.get("longitude", p.get("lon")),
                "lat": p.get("latitude", p.get("lat")),
                "lon": p.get("longitude", p.get("lon"))
            })

        # ── Packing Checklist tailored to Indian Travel ──────────────────
        packing_checklist = {
            "clothes": [
                "Light breathable cotton tops & comfortable trousers for day sightseeing",
                "Light jacket, sweater or shawl for cool mornings & evenings",
                "Sturdy walking shoes or sneakers with good traction",
                "Extra pair of comfortable socks and quick-dry apparel"
            ],
            "electronics": [
                "10,000mAh or 20,000mAh Power Bank with fast charging",
                "Phone charger, cables and universal travel adapter",
                "Camera / action cam with extra memory card",
                "Earphones / AirPods for long transit journeys"
            ],
            "medicines": [
                "Motion sickness relief (Avomine for mountain ghat roads)",
                "Pain relief spray (Volini) & Paracetamol tablets",
                "ORS rehydration sachets & Digestive tablets (Pudin Hara)",
                "Waterproof adhesive bandages & antiseptic wipes"
            ],
            "documents": [
                "Govt Photo ID (Aadhaar Card / Driving License / Passport)",
                "Train / bus reservation PDF or offline copies",
                "Base Camp hotel confirmation vouchers",
                "Emergency medical & travel contact slip"
            ],
            "accessories": [
                "UV400 Polarized Sunglasses & wide-brim sun hat",
                "Insulated 1L reusable stainless steel water flask",
                "Compact daypack (15–20 Litres) for daily sightseeing",
                "Compact umbrella or lightweight rain poncho"
            ],
            "destination_essentials": [
                "Mosquito & insect repellent spray (Odomos)",
                "High SPF Sunscreen (SPF 50+) for day outdoor excursions",
                "Physical cash reserve (₹3,000 in ₹100/₹200 notes for local stalls)",
                "Offline downloaded Google Maps for the destination zone"
            ]
        }

        # ── Day Planner pre-populated layout for instant drag-and-drop ───
        day_planner_dict = {}
        for day_obj in daily_itinerary:
            d_num = day_obj["day_number"]
            m_act = day_obj["morning"]
            a_act = day_obj["afternoon"]
            e_act = day_obj["evening"]
            day_planner_dict[str(d_num)] = {
                "morning": [{
                    "id": f"act_{d_num}_morn",
                    "icon": "🌅",
                    "name": m_act["name"],
                    "dur": m_act.get("dur", "2.5h"),
                    "type": "attraction",
                    "category": "Sightseeing",
                    "fee": m_act.get("fee_inr", 0),
                    "lat": m_act.get("lat"),
                    "lon": m_act.get("lon"),
                    "dist": 3.5
                }],
                "afternoon": [{
                    "id": f"act_{d_num}_aftn",
                    "icon": "☀️",
                    "name": a_act["name"],
                    "dur": a_act.get("dur", "3h"),
                    "type": "food" if "lunch" in a_act["name"].lower() else "attraction",
                    "category": "Sightseeing",
                    "fee": a_act.get("fee_inr", 0),
                    "lat": a_act.get("lat"),
                    "lon": a_act.get("lon"),
                    "dist": 5.2
                }],
                "evening": [{
                    "id": f"act_{d_num}_eve",
                    "icon": "🌆",
                    "name": e_act["name"],
                    "dur": e_act.get("dur", "2h"),
                    "type": "attraction",
                    "category": "Sightseeing",
                    "fee": e_act.get("fee_inr", 0),
                    "lat": e_act.get("lat"),
                    "lon": e_act.get("lon"),
                    "dist": 2.8
                }],
                "night": []
            }

        # Build authoritative timeline (includes Day 1 arrival, return-to-hotel & Day N return leg)
        authoritative_tl = build_timeline({
            "source": source,
            "destination": dest,
            "start_date": start_date if start_date not in ("2026-09-15", "2026-12-02", "") else "",
            "num_days": days,
            "num_travelers": travelers,
            "budget": budget,
            "transport": transport,
            "stay": base_camp_stay,
            "transit": {
                "mode": transport,
                "title": op_title,
                "fare_per_person": round_trip_pp,
                "departure": transit_info.get("departure_time", "06:00"),
                "duration_mins": dur_mins,
                "distance_km": round(approx_distance, 1),
            },
            "selected_attractions": selected_attractions,
        })

        # Sync budget_analysis with single-source-of-truth calculate_trip_total
        tl_b = authoritative_tl.get("budget") or {}
        if tl_b:
            denom = float(tl_b.get("budget_target") or budget or 1.0)
            budget_analysis["stay_cost_inr"] = tl_b.get("stay_group", budget_analysis.get("stay_cost_inr", 0))
            budget_analysis["transit_cost_inr"] = tl_b.get("transit_group", budget_analysis.get("transit_cost_inr", 0))
            budget_analysis["food_cost_inr"] = tl_b.get("food_group", budget_analysis.get("food_cost_inr", 0))
            budget_analysis["sightseeing_cost_inr"] = tl_b.get("entry_group", budget_analysis.get("sightseeing_cost_inr", 0))
            budget_analysis["emergency_buffer_inr"] = tl_b.get("misc_group", budget_analysis.get("emergency_buffer_inr", 0))
            budget_analysis["committed_total_inr"] = tl_b.get("group_total", budget_analysis.get("committed_total_inr", 0))
            budget_analysis["per_person_total_inr"] = tl_b.get("per_person_total", 0)
            budget_analysis["remaining_pocket_balance_inr"] = max(0, round(denom - float(budget_analysis["committed_total_inr"]), 2))
            budget_analysis["is_feasible"] = not bool(tl_b.get("is_over_target", False))
            budget_analysis["budget_status"] = "🟢 Within Target" if budget_analysis["is_feasible"] else "🟡 Over Target"
            denom = float(budget_analysis["committed_total_inr"] or 1.0)
            if isinstance(budget_analysis.get("breakdown"), dict):
                budget_analysis["breakdown"] = {
                    "accommodation": {
                        "amount": float(budget_analysis["stay_cost_inr"]),
                        "percentage": round((float(budget_analysis["stay_cost_inr"]) / denom) * 100, 1),
                        "details": f"Base camp stay ({max(1, days - 1)} nights)",
                    },
                    "transportation": {
                        "amount": float(budget_analysis["transit_cost_inr"]),
                        "percentage": round((float(budget_analysis["transit_cost_inr"]) / denom) * 100, 1),
                        "details": f"Round-trip {transport} transit ({travelers} pax)",
                    },
                    "food_and_dining": {
                        "amount": float(budget_analysis["food_cost_inr"]),
                        "percentage": round((float(budget_analysis["food_cost_inr"]) / denom) * 100, 1),
                        "details": f"Estimated meals ({days} days × {travelers} pax)",
                    },
                    "sightseeing_and_activities": {
                        "amount": float(budget_analysis["sightseeing_cost_inr"]),
                        "percentage": round((float(budget_analysis["sightseeing_cost_inr"]) / denom) * 100, 1),
                        "details": "Attraction entry fees",
                    },
                    "emergency_and_buffer": {
                        "amount": float(budget_analysis["emergency_buffer_inr"]),
                        "percentage": round((float(budget_analysis["emergency_buffer_inr"]) / denom) * 100, 1),
                        "details": "Local incidentals & contingency",
                    },
                }

        # ── Complete Itinerary Dictionary (matches view_trip.html bindings)
        unified_itinerary = {
            "trip_title": f"{days}-Day {dest.title()} Plan ({base_camp_stay['name']})",
            "destination": dest.title(),
            "duration_days": days,
            "travel_style": style.title(),
            "overview": f"Plan to {dest.title()} anchored at {base_camp_stay['name']} via {op_title}.",
            "trip_summary": f"{days}-day {style} plan to {dest.title()} anchored at {base_camp_stay['name']}.",
            "best_time_to_visit": "October to May",
            "local_language": "Kannada, Hindi, English" if "karnataka" in dest.lower() or any(k in dest.lower() for k in ("coorg", "mysuru", "mysore", "hampi", "bengaluru")) else "Regional & English",
            "currency": "₹ INR (Indian Rupee)",
            "time_zone": "IST (UTC+05:30)",
            "base_camp_stay": base_camp_stay,
            "transit": transit_info,
            "timeline": authoritative_tl,
            "selected_attractions": selected_attractions,
            "packing_checklist": packing_checklist,
            "days": daily_itinerary,
            "day_planner": day_planner_dict,
            "day_routes": [d["day_route"] for d in daily_itinerary if "day_route" in d],
            "emergency_numbers": {
                "police": "100",
                "ambulance": "108",
                "tourist_helpline": "1363",
                "disaster_management": "1070"
            }
        }

        # ── Assemble unified plan dictionary ─────────────────────────────
        return {
            "destination": dest.title(),
            "source": source.title(),
            "num_days": days,
            "num_travelers": travelers,
            "travel_style": style,
            "base_camp_stay": base_camp_stay,
            "transit": transit_info,
            "itinerary": unified_itinerary,
            "day_routes": unified_itinerary.get("day_routes", []),
            "budget": budget_analysis,
            "hotels": tiered_hotels,
            "emergency_support": base_camp_stay.get("emergency_support", {}),
            "pipeline_metadata": {
                "architecture": "Stay-First Multi-Agent Pipeline",
                "agents_used": [
                    "Geospatial & Transit",
                    "Itinerary Scheduling",
                    "Budget & Expense",
                    "Accommodations & Proximity"
                ]
            }
        }

