"""
TravelPlannerAgent - Main / Dashboard Routes (Blueprint)
"""

import os
from flask import (
    Blueprint, render_template, session, redirect, url_for, request, jsonify
)
from backend.routes.auth_routes import login_required
from backend.models.trip import get_trips_by_user, get_saved_trips
from backend.services.weather.weather_service import get_current_weather

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def home():
    """Landing / home page — Explore Destinations."""
    return render_template("planner/destinations.html")


@main_bp.route("/launchpad")
@main_bp.route("/welcome")
def launchpad():
    """Interactive creator launchpad — choose between Express AI and Custom Studio."""
    user_id = session.get("user_id")
    if not user_id:
        from backend.models.user import create_isolated_guest_user
        user_id = create_isolated_guest_user()
        session.permanent = True
        session["user_id"] = user_id
        session["user_name"] = "Traveler"
        session["user_role"] = "guest"
        session["is_guest"] = True

    user_name = session.get("user_name", "Traveler")
    destination = request.args.get("destination", "Coorg")
    source = request.args.get("source", "Bengaluru")
    trips = get_trips_by_user(user_id) if user_id else []
    recent_trips = trips[:3]
    return render_template(
        "planner/launchpad.html",
        user_name=user_name,
        destination=destination,
        source=source,
        recent_trips=recent_trips,
        trips_count=len(trips)
    )


@main_bp.route("/overview")
@main_bp.route("/home")
def overview():
    """Interactive journey overview & feature showcase."""
    return render_template("home.html")


@main_bp.route("/dashboard")
@login_required
def dashboard():
    """User dashboard — recent trips, saved trips, stats."""
    user_id = session["user_id"]
    trips        = get_trips_by_user(user_id)
    saved        = get_saved_trips(user_id)
    recent_trips = trips[:5]

    # Quick weather tip for most recent destination
    weather_summary = None
    if trips:
        dest = trips[0]["destination"]
        weather_summary = get_current_weather(dest)

    stats = {
        "total_trips":   len(trips),
        "saved_trips":   len(saved),
        "completed":     sum(1 for t in trips if t["status"] == "completed"),
        "total_budget":  sum(t["budget"] for t in trips)
    }

    return render_template("dashboard/dashboard.html",
        trips=recent_trips,
        saved=saved,
        stats=stats,
        weather=weather_summary
    )


@main_bp.route("/destinations")
def destinations_redirect():
    """Redirect root /destinations to planner destinations catalog."""
    return redirect(url_for("planner.destinations"), code=302)


@main_bp.route("/wizard")
def wizard_redirect():
    """Redirect root /wizard to planner wizard."""
    return redirect(url_for("planner.wizard"), code=302)


@main_bp.route("/new")
def new_trip_redirect():
    """Redirect root /new to planner new trip."""
    return redirect(url_for("planner.new_trip"), code=302)


@main_bp.route("/datasets")
def datasets_showcase():
    """Showcase of datasets redirecting to destinations explorer."""
    return redirect(url_for("planner.destinations"))


_DIAGRAMS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "diagrams"))


@main_bp.route("/architecture")
def view_architecture():
    """Interactive Archify Architecture Diagram with all 4 datasets & agents."""
    from flask import send_from_directory
    return send_from_directory(_DIAGRAMS_DIR, "travel-planner-architecture.html")


@main_bp.route("/workflow")
def view_workflow():
    """Interactive Archify Workflow Diagram."""
    from flask import send_from_directory
    target = "travel-planner-workflow.html" if os.path.exists(os.path.join(_DIAGRAMS_DIR, "travel-planner-workflow.html")) else "travel-planner-architecture.html"
    return send_from_directory(_DIAGRAMS_DIR, target)



@main_bp.route("/api/travel-concierge", methods=["POST"])
def travel_concierge():
    """Granite AI travel concierge instant answering service."""
    data = request.get_json() or {}
    query = (data.get("query") or "").strip()
    if not query:
        return jsonify({"success": False, "answer": "Please ask a travel question or click one of the suggested prompts!"})

    q_lower = query.lower()

    # Pre-compiled high-accuracy responses for popular queries + fallback
    curated_answers = {
        "ooty": "☕ **Ooty Travel Tips:**\n• **Best Cafes:** Earl's Secret, Place to Bee, Modern Store (homemade chocolates & fudge).\n• **Transit:** Driving up via Kalhatti Ghat has 36 hairpin bends (open downhill only via Gudalur for small cars). Ensure good brakes and day driving.\n• **Weather:** Nights dip to 10°C–14°C year-round. Light jackets and walking shoes are recommended.",
        "coorg": "🌿 **Coorg (Kodagu) Essentials:**\n• **Route:** Bengaluru to Coorg via Mysore expressway + Hunsur is ~5.5 hrs. Road conditions are smooth with scenic paddy fields.\n• **Base Camps:** Stay in coffee estate homestays around Madikeri or Kushalnagar for authentic Kodava cuisine (Pandi curry, Kadambuttu).\n• **Highlights:** Abbey Falls, Raja's Seat sunset, Namdroling Golden Temple.",
        "hampi": "🏛️ **Hampi UNESCO Guide:**\n• **Attractions:** Stone Chariot at Vijaya Vittala Temple, Virupaksha, and sunset from Matanga Hill or Hemakuta.\n• **Transport:** Rent a bicycle or electric scooter (₹300/day). Sunscreen and grip footwear are essential for stone climbing.\n• **Best Season:** October to March.",
        "chikmagalur": "🏔️ **Chikmagalur Peak Guide:**\n• **Mullayanagiri Peak:** Highest peak in Karnataka. Best visited before 8:30 AM to catch the cloud carpet before the fog lifts.\n• **Coffee Estates:** Tour Baba Budangiri and hire a local Jeep for Hebbe Falls.\n• **Transit:** ~4.5 hours from Bengaluru via NH75.",
        "gokarna": "🏖️ **Gokarna & Beach Treks:**\n• **The 5-Beach Trek:** Kudle → Om Beach → Half Moon → Paradise Beach. Take local ferry boats back from Paradise if tired.\n• **Atmosphere:** Spiritual temple town meets pristine, laid-back Arabian Sea cliffs.\n• **Best Stay:** Cliff-side cottages overlooking Kudle Beach.",
        "train": "🚂 **IRCTC Rail vs KSRTC Airavat Buses:**\n• **For Mysore/Ooty:** The Vande Bharat Express (SBC → MYS in 1h 45m) followed by KSRTC or taxi to Ooty is the most comfortable.\n• **For Coastal Karnataka (Gokarna):** The Panchaganga Express or KSRTC Club Class overnight sleeper is ideal.",
        "budget": "💰 **Indian Travel Budget Breakdown:**\n• **Base Camp Homestays/Hotels:** ~40% of total spend.\n• **Transit (Fuel / Rail / Buses):** ~30% of total spend.\n• **Sights & Entry Fees:** ~18% (most Indian ASI monuments are ₹25–₹50).\n• **Food & Buffer:** ~12% for authentic local meals."
    }

    matched_key = None
    for k in curated_answers:
        if k in q_lower:
            matched_key = k
            break

    if matched_key:
        answer = curated_answers[matched_key]
    else:
        # Try Granite AI if credentials exist, else structured expert travel advisor response
        try:
            from backend.services.granite.granite_service import call_granite
            prompt = f"You are Yatrika's Indian Travel Concierge. Answer this traveler's question concisely in 3-4 bullet points with practical tips, road advice, and stay recommendations:\nQuestion: {query}\nConcise Advice:"
            answer = call_granite(prompt, max_tokens=300)
        except Exception:
            answer = f"🧭 **Yatrika Travel Advice for '{query}':**\n• Plan multi-day itineraries with a central Base Camp stay to minimize luggage transfers.\n• Choose morning travel slots (departure before 7:00 AM) to beat city exit traffic.\n• Always keep ₹1,500–₹2,000 in physical cash for local viewpoint parking & toll booths.\n• Use Yatrika's Custom Step Studio to customize attraction visit times."

    return jsonify({"success": True, "answer": answer, "query": query})




