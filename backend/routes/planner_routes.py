"""
TravelPlannerAgent - Travel Planner Routes (Blueprint)
"""

import json
from flask import (
    Blueprint, request, render_template, redirect,
    url_for, session, flash, jsonify, send_file
)
from backend.routes.auth_routes import login_required
from backend.models.trip import (
    get_trip_by_id, get_trips_by_user,
    delete_trip, save_trip,
    get_saved_trips, unsave_trip, add_expense, get_expenses
)
from backend.services.weather.weather_service import (
    get_current_weather, get_forecast, get_travel_weather_advice
)
from backend.services.pdf.pdf_service import generate_trip_pdf

planner_bp = Blueprint("planner", __name__, url_prefix="/planner")


@planner_bp.route("/wizard")
@login_required
def wizard():
    """Smart Travel Planning Wizard — interactive 10-step frontend workflow."""
    return render_template("planner/wizard.html")


@planner_bp.route("/destinations")
def destinations():
    """Destinations explorer page."""
    return render_template("planner/destinations.html")


@planner_bp.route("/destinations/<slug>")
def destination_detail(slug: str):
    """Individual destination detail page."""
    return render_template("planner/destination_detail.html", slug=slug)


@planner_bp.route("/new", methods=["GET", "POST"])
@login_required
def new_trip():
    """Travel Planner form — collect trip details and generate AI itinerary."""
    from datetime import date
    from backend.models.trip import create_trip, update_trip_itinerary
    from backend.services.granite.granite_service import generate_complete_travel_plan
    
    today = date.today().isoformat()
    
    if request.method == "POST":
        destination   = request.form.get("destination", "").strip()
        start_date    = request.form.get("start_date")
        end_date      = request.form.get("end_date")
        num_days      = int(request.form.get("num_days", 1))
        budget        = float(request.form.get("budget", 1000))
        num_travelers = int(request.form.get("num_travelers", 1))
        travel_style  = request.form.get("travel_style", "budget")
        transport     = request.form.get("transport", "flight")
        interests     = request.form.getlist("interests")
        special_reqs  = request.form.getlist("special_requirements")

        if not destination:
            flash("Please enter a destination.", "danger")
            return redirect(url_for("planner.new_trip"))

        trip_data = {
            "destination":           destination,
            "start_date":            start_date,
            "end_date":              end_date,
            "num_days":              num_days,
            "budget":                budget,
            "num_travelers":         num_travelers,
            "travel_style":          travel_style,
            "transport":             transport,
            "interests":             interests,
            "special_requirements":  special_reqs
        }

        # Create initial trip record (status = draft)
        trip_id = create_trip(session["user_id"], trip_data)

        # Call IBM Granite LLM API
        flash("Generating your AI itinerary with IBM Granite…", "info")
        try:
            ai_result = generate_complete_travel_plan(trip_data)
        except Exception as e:
            ai_result = {
                "itinerary": {"error": str(e)},
                "budget":    {}, "hotels": {}, "transport": {}, "food": {}
            }
            flash(f"AI generation warning: {e}", "warning")

        # Fetch OpenWeatherMap advice & forecast
        weather_current  = get_current_weather(destination)
        weather_forecast = get_forecast(destination)
        weather_advice   = get_travel_weather_advice(weather_current)
        weather_data = {
            "current":  weather_current,
            "forecast": weather_forecast.get("forecast", []),
            "alerts":   weather_advice
        }

        # Update the database record with the full data
        update_trip_itinerary(
            trip_id,
            ai_result.get("itinerary", {}),
            weather_data,
            ai_result.get("budget", {}),
            ai_result.get("hotels", {})
        )

        flash("Trip planned and saved successfully!", "success")
        return redirect(url_for("planner.view_trip", trip_id=trip_id))

    # For GET, pre-populate if values are passed in the request arguments
    values = {
        "destination": request.args.get("destination", ""),
        "start_date": request.args.get("start_date", ""),
        "end_date": request.args.get("end_date", ""),
        "num_days": request.args.get("num_days", "3"),
        "num_travelers": request.args.get("num_travelers", "1"),
        "budget": request.args.get("budget", "1500"),
        "travel_style": request.args.get("travel_style", "budget"),
        "transport": request.args.get("transport", "flight")
    }
    
    return render_template("planner/new_trip.html", today=today, values=values)


@planner_bp.route("/save_wizard", methods=["POST"])
@login_required
def save_wizard():
    """Save the customized itinerary directly from the Smart Travel Wizard to the DB."""
    from backend.models.trip import create_trip, update_trip_itinerary
    import requests as req

    try:
        data = request.get_json() or {}
        destination = data.get("destination", "").strip()
        start_date = data.get("start_date")
        end_date = data.get("end_date")
        num_days = int(data.get("num_days", 1))
        budget = float(data.get("budget", 1000))
        num_travelers = int(data.get("num_travelers", 1))
        travel_style = data.get("travel_style", "budget")
        transport = data.get("transport", "flight")
        
        # Selected attractions from frontend
        selected_attractions = data.get("selected_attractions", [])
        day_planner = data.get("day_planner", {})
        weather_state = data.get("weather", {})

        # ── Auto-distribute attractions across days when the day planner
        #    was not used (day_planner is empty or has no assigned activities)
        def _is_planner_empty(dp):
            """Return True if no attraction was placed in any day/zone."""
            for day_obj in dp.values():
                if isinstance(day_obj, dict):
                    for acts in day_obj.values():
                        if acts:
                            return False
            return True

        if selected_attractions and _is_planner_empty(day_planner):
            # Distribute attractions evenly across days in morning/afternoon/evening slots
            zones = ["morning", "afternoon", "evening"]
            day_planner = {str(d): {"morning": [], "afternoon": [], "evening": [], "night": []} for d in range(1, num_days + 1)}
            for i, attr in enumerate(selected_attractions):
                day_key = str((i % num_days) + 1)
                zone = zones[i // num_days % len(zones)]
                day_planner[day_key][zone].append({
                    "id":       attr.get("id", ""),
                    "icon":     attr.get("icon", "📍"),
                    "name":     attr.get("name", "—"),
                    "dur":      attr.get("dur", "2h"),
                    "type":     "attraction",
                    "category": attr.get("cat", attr.get("category", "")),
                    "fee":      attr.get("fee", 0),
                })
        
        # Calculate costs for the budget breakdown
        fuel_cost = 0
        if transport == "bike":
            total_dist = sum(a.get("dist", 0) for a in selected_attractions)
            fuel_cost = round(total_dist / 30 * 110)
        else:
            total_dist = sum(a.get("dist", 0) for a in selected_attractions)
            fuel_cost = round(total_dist / 12 * 100)
            
        entry_fees = sum(a.get("fee", 0) for a in selected_attractions)
        food_cost = num_travelers * num_days * 600
        hotel_cost = num_days * 2000
        shopping_cost = num_travelers * 500
        total_spend = fuel_cost + entry_fees + food_cost + hotel_cost + shopping_cost

        # Construct budget JSON
        budget_pct_denom = total_spend if total_spend > 0 else 1
        budget_json = {
            "total_budget": total_spend,
            "daily_average": total_spend / num_days if num_days > 0 else total_spend,
            "budget_status": "comfortable" if budget >= total_spend else "tight",
            "breakdown": {
                "fuel": {"amount": fuel_cost, "percentage": (fuel_cost / budget_pct_denom) * 100, "details": f"Estimated fuel cost for travel mode: {transport.title()}"},
                "entry_fees": {"amount": entry_fees, "percentage": (entry_fees / budget_pct_denom) * 100, "details": "Entry fees for selected attractions"},
                "food": {"amount": food_cost, "percentage": (food_cost / budget_pct_denom) * 100, "details": f"Food allowance for {num_travelers} traveler(s)"},
                "hotel": {"amount": hotel_cost, "percentage": (hotel_cost / budget_pct_denom) * 100, "details": f"Accommodation for {num_days} day(s)"},
                "shopping": {"amount": shopping_cost, "percentage": (shopping_cost / budget_pct_denom) * 100, "details": "Estimated shopping/miscellaneous expense"}
            },
            "saving_tips": [
                "Utilize local or public transport for sightseeing when possible.",
                "Choose local food establishments to experience authentic cuisine and save money.",
                "Prioritize free-entry natural viewpoints and public historical sites."
            ]
        }

        # Build day-by-day itinerary
        itinerary_days = []
        for d in range(1, num_days + 1):
            day_key = str(d)
            day_plan = day_planner.get(day_key, {})

            # Map ALL attractions per slot — keep full list so every place is shown
            morning_acts   = day_plan.get("morning", [])
            afternoon_acts = day_plan.get("afternoon", [])
            evening_acts   = day_plan.get("evening", []) + day_plan.get("night", [])

            def make_places(acts, fallback_activity, tip):
                if not acts:
                    return None
                # Primary display still uses first item for legacy fields
                first = acts[0]
                return {
                    "activity":  first.get("name", fallback_activity),
                    "place":     first.get("name", destination),
                    "duration":  first.get("dur", "2h"),
                    "entry_fee": f"₹{first.get('fee', 0)}" if first.get("fee") else "Free",
                    "tips": tip,
                    # Full list for rich display in view_trip.html
                    "places": [
                        {
                            "id":       a.get("id", ""),
                            "name":     a.get("name", "—"),
                            "category": a.get("category", a.get("cat", "")),
                            "duration": a.get("dur", "2h"),
                            "fee":      f"₹{a['fee']}" if a.get("fee") else "Free",
                            "raw_fee":  a.get("fee", 0),
                            "icon":     a.get("icon", "📍"),
                            "lat":      a.get("lat"),
                            "lon":      a.get("lon"),
                            "dist":     a.get("dist", 0)
                        }
                        for a in acts
                    ]
                }

            itinerary_days.append({
                "day":       d,
                "theme":     f"Exploring {destination}",
                "date":      f"Day {d}",
                "morning":   make_places(morning_acts,   "Sightseeing and leisure",      "Carry a camera and light jacket."),
                "afternoon": make_places(afternoon_acts, "Exploring local spots",        "Try local food nearby."),
                "evening":   make_places(evening_acts,   "Relaxing in the evening",      "Perfect time for photography."),
                "food_recommendations": [
                    {"meal": "Breakfast", "restaurant": "Local Cafe",         "cuisine": "Local Coffee & Snacks", "price_range": "₹"},
                    {"meal": "Lunch",     "restaurant": "Traditional Diner",   "cuisine": "Traditional meals",   "price_range": "₹₹"},
                    {"meal": "Dinner",    "restaurant": "Central Restaurant",   "cuisine": "Multi-cuisine",       "price_range": "₹₹"}
                ],
                "daily_budget": round(total_spend / num_days) if num_days > 0 else total_spend,
                "local_tips": "Interact with locals to discover off-beat locations.",
                "hidden_gems": ["Secret viewpoint nearby", "Local handicraft market"]
            })
            
        # Rich, contextual packing checklist based on travel style and transport mode
        packing_list = {
            "clothes": ["Comfortable walking shoes", "T-shirts & casual wear", "Light jacket", "Umbrella or raincoat"],
            "accessories": ["Sunglasses", "Reusable water bottle", "Daypack", "Sunscreen (SPF 50)", "Hat or cap"],
            "electronics": ["Phone & charger", "Power bank", "Universal adapter"],
            "documents": ["Govt-issued ID", "Hotel booking vouchers", "Cash & cards"],
            "medicines": ["Pain relievers", "Antacids", "Band-aids & antiseptic cream", "Personal prescription meds"]
        }

        # Add travel-style specific items
        style_lower = travel_style.lower()
        if "adventure" in style_lower:
            packing_list["clothes"].extend(["Trekking shoes", "Breathable activewear"])
            packing_list["accessories"].extend(["Insect repellent", "Flashlight/Headlamp", "Pocket multi-tool"])
        elif "nature" in style_lower:
            packing_list["accessories"].extend(["Binoculars", "Insect repellent"])
            packing_list["clothes"].append("Rainproof windbreaker")
        elif "photography" in style_lower:
            packing_list["electronics"].extend(["Tripod", "Lens cleaning kit", "Spare memory cards", "Extra camera batteries"])
        elif "spiritual" in style_lower:
            packing_list["clothes"].extend(["Modest/traditional clothing", "Slip-on footwear"])
        elif "luxury" in style_lower:
            packing_list["clothes"].extend(["Semi-formal dinner wear", "Swimwear"])
            packing_list["accessories"].append("Travel organizer")
        elif "budget" in style_lower:
            packing_list["accessories"].extend(["Reusable shopping bag", "Travel mug"])

        # Add transport-specific items
        transport_lower = transport.lower()
        if "car" in transport_lower or "bike" in transport_lower:
            packing_list["documents"].append("Vehicle registration & insurance documents")
            packing_list["accessories"].append("Car/Bike charger adapter")
            if "bike" in transport_lower:
                packing_list["clothes"].extend(["Riding jacket & gloves", "Helmet"])
                packing_list["accessories"].append("Bungee ropes")
        elif "flight" in transport_lower:
            packing_list["documents"].extend(["Boarding pass", "Luggage tags"])
            packing_list["accessories"].append("Travel neck pillow")

        itinerary_json = {
            "trip_summary": f"Customized trip to {destination} planned via the Smart Travel Wizard.",
            "best_time_to_visit": "October to March",
            "local_language": "Local Regional Language",
            "currency": "INR (₹)",
            "time_zone": "IST (UTC+5:30)",
            "days": itinerary_days,
            "safety_tips": [
                "Keep emergency contact numbers handy.",
                "Check local weather forecast before driving/riding.",
                "Respect local culture and dress codes at spiritual sites."
            ],
            "emergency_numbers": {
                "police": "100",
                "ambulance": "108",
                "tourist_helpline": "1363"
            },
            "packing_checklist": packing_list,
            "selected_attractions": selected_attractions,
            "day_planner": day_planner
        }
        
        # Populate live weather details
        weather_data = weather_state
        if not weather_data or "current" not in weather_data or not weather_data["current"]:
            # Fetch weather live in the backend
            weather_current  = get_current_weather(destination)
            weather_forecast = get_forecast(destination)
            weather_advice   = get_travel_weather_advice(weather_current)
            weather_data = {
                "current":  weather_current,
                "forecast": weather_forecast.get("forecast", []),
                "alerts":   weather_advice
            }
        else:
            # Normalize forecast list to be a list of forecast days
            raw_forecast = weather_data.get("forecast", {})
            if isinstance(raw_forecast, dict):
                weather_data["forecast"] = raw_forecast.get("forecast", [])
            
        # Fetch real hotels from Nominatim
        hotels_data = {
            "budget_hotels": [],
            "mid_range_hotels": [],
            "luxury_hotels": [],
            "booking_advice": "Compare prices across multiple booking platforms."
        }
        try:
            url = f"https://nominatim.openstreetmap.org/search?q=hotel+in+{req.utils.quote(destination)}&format=json&limit=9"
            resp = req.get(url, headers={"User-Agent": "TravelPlannerAgent/1.0 (ibm-project)"}, timeout=5)
            if resp.ok:
                elements = resp.json()
                for idx, el in enumerate(elements):
                    name = el.get("display_name", "").split(",")[0]
                    h_obj = {
                        "name": name,
                        "rating": round(3.8 + (idx % 3) * 0.4 + (idx % 2) * 0.2, 1),
                        "price_per_night": 1500 + (idx % 3) * 2000 + (idx % 2) * 1000,
                        "distance_from_center": f"{round(0.5 + idx * 0.8, 1)} km from center",
                        "amenities": ["Free Wi-Fi", "AC", "Room Service"] if idx % 2 == 0 else ["Free Wi-Fi", "AC", "Breakfast Included", "Parking"],
                        "booking_tip": "Highly rated by recent travelers."
                    }
                    if idx < 3:
                        hotels_data["budget_hotels"].append(h_obj)
                    elif idx < 6:
                        hotels_data["mid_range_hotels"].append(h_obj)
                    else:
                        hotels_data["luxury_hotels"].append(h_obj)
        except Exception:
            pass

        # If Nominatim returned no hotels, use mock/fallback list
        if not hotels_data["budget_hotels"]:
            hotels_data = {
                "budget_hotels": [
                    {"name": f"{destination} Backpackers Stay", "rating": 4.1, "price_per_night": 1200, "distance_from_center": "1.2 km from center", "amenities": ["Free Wi-Fi", "Dorm beds", "Cafe"], "booking_tip": "Great for solo travelers."}
                ],
                "mid_range_hotels": [
                    {"name": f"The {destination} Inn", "rating": 4.3, "price_per_night": 3500, "distance_from_center": "0.5 km from center", "amenities": ["Free Wi-Fi", "AC", "Room Service", "Breakfast"], "booking_tip": "Family friendly."}
                ],
                "luxury_hotels": [
                    {"name": f"{destination} Resort & Spa", "rating": 4.7, "price_per_night": 8500, "distance_from_center": "3.5 km from center", "amenities": ["Free Wi-Fi", "AC", "Swimming Pool", "Spa", "Restaurant"], "booking_tip": "Scenic views."}
                ],
                "booking_advice": "Book early to secure premium resort views."
            }

        # Create database record
        trip_data = {
            "destination": destination,
            "start_date": start_date,
            "end_date": end_date,
            "num_days": num_days,
            "budget": budget,
            "num_travelers": num_travelers,
            "travel_style": travel_style,
            "transport": transport,
            "interests": [],
            "special_requirements": []
        }
        trip_id = create_trip(session["user_id"], trip_data)

        # Persist full JSON records
        update_trip_itinerary(
            trip_id,
            itinerary_json,
            weather_data,
            budget_json,
            hotels_data
        )

        # Save to saved_trips table also
        save_trip(session["user_id"], trip_id, notes="Planned via Smart Travel Wizard")

        return jsonify({"success": True, "trip_id": trip_id})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@planner_bp.route("/<int:trip_id>/update_planner", methods=["POST"])
@login_required
def update_planner(trip_id: int):
    """Update trip's day planner layout and persist back to database."""
    from backend.database.db import execute_query
    trip = get_trip_by_id(trip_id)
    if not trip or trip["user_id"] != session["user_id"]:
        return jsonify({"success": False, "error": "Trip not found."}), 404

    try:
        data = request.get_json() or {}
        day_planner = data.get("day_planner", {})
        
        itinerary = json.loads(trip["itinerary_json"] or "{}")
        destination = trip["destination"]
        num_days = trip["num_days"]
        num_travelers = trip["num_travelers"]
        
        # Build day-by-day itinerary
        itinerary_days = []
        for d in range(1, num_days + 1):
            day_key = str(d)
            day_plan = day_planner.get(day_key, {})

            morning_acts   = day_plan.get("morning", [])
            afternoon_acts = day_plan.get("afternoon", [])
            evening_acts   = day_plan.get("evening", []) + day_plan.get("night", [])

            def make_places(acts, fallback_activity, tip):
                if not acts:
                    return None
                first = acts[0]
                return {
                    "activity":  first.get("name", fallback_activity),
                    "place":     first.get("name", destination),
                    "duration":  first.get("dur", "2h"),
                    "entry_fee": f"₹{first.get('fee', 0)}" if first.get("fee") else "Free",
                    "tips": tip,
                    "places": [
                        {
                            "id":       a.get("id", ""),
                            "name":     a.get("name", "—"),
                            "category": a.get("category", a.get("cat", "")),
                            "duration": a.get("dur", "2h"),
                            "fee":      f"₹{a['fee']}" if a.get("fee") else "Free",
                            "raw_fee":  a.get("fee", 0),
                            "icon":     a.get("icon", "📍"),
                            "lat":      a.get("lat"),
                            "lon":      a.get("lon"),
                            "dist":     a.get("dist", 0)
                        }
                        for a in acts
                    ]
                }

            itinerary_days.append({
                "day":       d,
                "theme":     f"Exploring {destination}",
                "date":      f"Day {d}",
                "morning":   make_places(morning_acts,   "Sightseeing and leisure",      "Carry a camera and light jacket."),
                "afternoon": make_places(afternoon_acts, "Exploring local spots",        "Try local food nearby."),
                "evening":   make_places(evening_acts,   "Relaxing in the evening",      "Perfect time for photography."),
                "food_recommendations": [
                    {"meal": "Breakfast", "restaurant": "Local Cafe",         "cuisine": "Local Coffee & Snacks", "price_range": "₹"},
                    {"meal": "Lunch",     "restaurant": "Traditional Diner",   "cuisine": "Traditional meals",   "price_range": "₹₹"},
                    {"meal": "Dinner",    "restaurant": "Central Restaurant",   "cuisine": "Multi-cuisine",       "price_range": "₹₹"}
                ],
                "daily_budget": 0,
                "local_tips": "Interact with locals to discover off-beat locations.",
                "hidden_gems": ["Secret viewpoint nearby", "Local handicraft market"]
            })

        # Recalculate cost estimate based on new sequence
        selected_attractions = itinerary.get("selected_attractions", [])
        entry_fees = sum(a.get("fee", 0) for a in selected_attractions)
        food_cost = num_travelers * num_days * 600
        hotel_cost = num_days * 2000
        shopping_cost = num_travelers * 500
        
        transport = trip["transport"]
        if transport == "bike":
            total_dist = sum(a.get("dist", 0) for a in selected_attractions)
            fuel_cost = round(total_dist / 30 * 110)
        else:
            total_dist = sum(a.get("dist", 0) for a in selected_attractions)
            fuel_cost = round(total_dist / 12 * 100)
            
        total_spend = fuel_cost + entry_fees + food_cost + hotel_cost + shopping_cost
        
        # Update daily budget values
        for day in itinerary_days:
            day["daily_budget"] = round(total_spend / num_days) if num_days > 0 else total_spend

        # Re-save to db
        itinerary["days"] = itinerary_days
        itinerary["day_planner"] = day_planner
        
        # update budget_json total spend
        budget = json.loads(trip["budget_json"] or "{}")
        budget["total_budget"] = total_spend
        budget["daily_average"] = total_spend / num_days if num_days > 0 else total_spend
        if "breakdown" in budget:
            budget["breakdown"]["entry_fees"]["amount"] = entry_fees
            budget["breakdown"]["fuel"]["amount"] = fuel_cost
            budget_pct_denom = total_spend if total_spend > 0 else 1
            for k in budget["breakdown"]:
                budget["breakdown"][k]["percentage"] = (budget["breakdown"][k]["amount"] / budget_pct_denom) * 100

        execute_query("""
            UPDATE trips
            SET itinerary_json = ?,
                budget_json = ?
            WHERE id = ?
        """, (json.dumps(itinerary), json.dumps(budget), trip_id))

        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@planner_bp.route("/share/<int:trip_id>")
def share_trip(trip_id: int):
    """Public shareable view of a trip itinerary."""
    trip = get_trip_by_id(trip_id)
    if not trip:
        flash("Trip not found.", "warning")
        return redirect(url_for("main.dashboard"))

    itinerary  = json.loads(trip["itinerary_json"] or "{}")
    weather    = json.loads(trip["weather_json"]   or "{}")
    budget     = json.loads(trip["budget_json"]    or "{}")
    hotels     = json.loads(trip["hotels_json"]    or "{}")
    expenses   = get_expenses(trip_id)

    return render_template("planner/view_trip.html",
        trip=trip,
        itinerary=itinerary,
        weather=weather,
        budget=budget,
        hotels=hotels,
        expenses=expenses,
        is_shared=True
    )


@planner_bp.route("/<int:trip_id>")
@login_required
def view_trip(trip_id: int):
    """Full itinerary view for a trip."""
    trip = get_trip_by_id(trip_id)
    if not trip or trip["user_id"] != session["user_id"]:
        flash("Trip not found.", "warning")
        return redirect(url_for("main.dashboard"))

    itinerary  = json.loads(trip["itinerary_json"] or "{}")
    weather    = json.loads(trip["weather_json"]   or "{}")
    budget     = json.loads(trip["budget_json"]    or "{}")
    hotels     = json.loads(trip["hotels_json"]    or "{}")
    expenses   = get_expenses(trip_id)

    return render_template("planner/view_trip.html",
        trip=trip,
        itinerary=itinerary,
        weather=weather,
        budget=budget,
        hotels=hotels,
        expenses=expenses
    )


@planner_bp.route("/<int:trip_id>/delete", methods=["POST"])
@login_required
def delete_trip_route(trip_id: int):
    """Delete a user's trip."""
    delete_trip(trip_id, session["user_id"])
    flash("Trip deleted.", "success")
    return redirect(url_for("main.dashboard"))


@planner_bp.route("/<int:trip_id>/save", methods=["POST"])
@login_required
def save_trip_route(trip_id: int):
    """Save a trip to favourites."""
    notes = request.form.get("notes", "")
    save_trip(session["user_id"], trip_id, notes)
    flash("Trip saved!", "success")
    return redirect(url_for("planner.view_trip", trip_id=trip_id))


@planner_bp.route("/saved")
@login_required
def saved_trips():
    """List saved/favourite trips."""
    trips = get_saved_trips(session["user_id"])
    return render_template("planner/saved_trips.html", trips=trips)


@planner_bp.route("/saved/<int:saved_id>/remove", methods=["POST"])
@login_required
def remove_saved(saved_id: int):
    """Remove a trip from saved."""
    unsave_trip(saved_id, session["user_id"])
    flash("Removed from saved trips.", "info")
    return redirect(url_for("planner.saved_trips"))


@planner_bp.route("/<int:trip_id>/pdf")
@login_required
def download_pdf(trip_id: int):
    """Generate and serve a PDF report for the trip."""
    trip = get_trip_by_id(trip_id)
    if not trip or trip["user_id"] != session["user_id"]:
        flash("Trip not found.", "warning")
        return redirect(url_for("main.dashboard"))

    itinerary = json.loads(trip["itinerary_json"] or "{}")
    budget    = json.loads(trip["budget_json"]    or "{}")
    hotels    = json.loads(trip["hotels_json"]    or "{}")
    weather   = json.loads(trip["weather_json"]   or "{}")

    try:
        pdf_path = generate_trip_pdf(trip, itinerary, budget, hotels, weather)
        return send_file(
            pdf_path,
            as_attachment=True,
            download_name=f"TravelPlan_{trip['destination'].replace(' ', '_')}.pdf",
            mimetype="application/pdf"
        )
    except Exception as e:
        flash(f"PDF generation failed: {e}", "danger")
        return redirect(url_for("planner.view_trip", trip_id=trip_id))


@planner_bp.route("/<int:trip_id>/expense", methods=["POST"])
@login_required
def add_expense_route(trip_id: int):
    """Add a manual expense entry."""
    category    = request.form.get("category", "miscellaneous")
    amount      = float(request.form.get("amount", 0))
    description = request.form.get("description", "")
    add_expense(trip_id, category, amount, description)
    flash("Expense added.", "success")
    return redirect(url_for("planner.view_trip", trip_id=trip_id))


# ── API Endpoints ─────────────────────────────────────────────

@planner_bp.route("/api/weather/<city>")
def weather_api(city: str):
    """JSON weather endpoint for frontend fetch."""
    current  = get_current_weather(city)
    forecast = get_forecast(city)
    alerts   = get_travel_weather_advice(current)
    return jsonify({"current": current, "forecast": forecast, "alerts": alerts})


@planner_bp.route("/api/osrm")
def osrm_proxy():
    """
    Proxy for the OSRM routing API.
    Forwards coordinate pairs to the public OSRM server with a proper
    User-Agent so it isn't rate-limited.
    Query params: profile, coords  (e.g. profile=car&coords=lon1,lat1;lon2,lat2)
    """
    import requests as req
    profile = request.args.get("profile", "car")
    coords  = request.args.get("coords", "")
    if not coords:
        return jsonify({"code": "Error", "message": "coords required"}), 400

    params = {
        "overview": request.args.get("overview", "false"),
        "alternatives": request.args.get("alternatives", "false"),
        "steps": request.args.get("steps", "false"),
        "geometries": request.args.get("geometries", "geojson")
    }
    url = f"https://router.project-osrm.org/route/v1/{profile}/{coords}"
    try:
        resp = req.get(
            url,
            params=params,
            headers={"User-Agent": "TravelPlannerAgent/1.0 (ibm-project)"},
            timeout=10,
        )
        return jsonify(resp.json() if resp.ok else {"code": "Error"})
    except Exception:
        return jsonify({"code": "Error"})



@planner_bp.route("/api/geocode")
def geocode_proxy():
    """
    Proxy for Nominatim geocoding API.
    Browsers cannot set the User-Agent header required by Nominatim's
    usage policy, so all geocoding requests are routed through here.
    """
    import requests as req
    q     = request.args.get("q", "").strip()
    limit = request.args.get("limit", "8")
    if not q:
        return jsonify([])
    url = (
        "https://nominatim.openstreetmap.org/search"
        f"?q={req.utils.quote(q)}&format=json&limit={limit}&addressdetails=1"
    )
    try:
        resp = req.get(
            url,
            headers={
                "User-Agent": "TravelPlannerAgent/1.0 (ibm-project)",
                "Accept-Language": "en",
            },
            timeout=10,
        )
        return jsonify(resp.json() if resp.ok else [])
    except Exception:
        return jsonify([])


# List of Overpass mirrors to try in order
_OVERPASS_MIRRORS = [
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass-api.de/api/interpreter",
    "https://overpass.openstreetmap.fr/api/interpreter",
]

_OVERPASS_HEADERS = {
    "User-Agent": "TravelPlannerAgent/1.0 (ibm-project; contact: ibm-project@travel.local)",
    "Accept": "application/json",
    "Content-Type": "application/x-www-form-urlencoded",
}


@planner_bp.route("/api/overpass", methods=["POST"])
def overpass_proxy():
    """
    Proxy for the Overpass API with automatic mirror fallback.
    Routes requests through the backend so the correct User-Agent is sent
    (required by overpass.kumi.systems to avoid rate-limiting).
    Tries multiple public mirrors if the first one is unavailable.
    """
    import requests as req
    body = request.get_data(as_text=True)   # expects: data=<ql>
    if not body:
        return jsonify({"elements": []})

    for mirror in _OVERPASS_MIRRORS:
        try:
            resp = req.post(
                mirror,
                data=body,
                headers=_OVERPASS_HEADERS,
                timeout=25,          # 25 s per mirror — 3 mirrors = 75 s max
            )
            if resp.ok:
                return jsonify(resp.json())
            # 429 = rate limited, try next mirror; other errors also try next
        except Exception:
            pass  # network error or timeout, try next mirror

    # All mirrors failed
    return jsonify({"elements": []})

