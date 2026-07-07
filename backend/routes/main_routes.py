"""
TravelPlannerAgent - Main / Dashboard Routes (Blueprint)
"""

from flask import (
    Blueprint, render_template, session, redirect, url_for
)
from backend.routes.auth_routes import login_required
from backend.models.trip import get_trips_by_user, get_saved_trips
from backend.services.weather.weather_service import get_current_weather

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def home():
    """Landing / home page."""
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
