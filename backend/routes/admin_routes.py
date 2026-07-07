"""
TravelPlannerAgent - Admin Routes (Blueprint)
"""

from flask import Blueprint, render_template, redirect, url_for, session, flash, jsonify
from backend.routes.auth_routes import login_required, admin_required
from backend.models.user import get_all_users, count_users, delete_user
from backend.models.trip import (
    get_all_trips, count_trips, get_top_destinations
)

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/")
@login_required
@admin_required
def admin_dashboard():
    """Admin overview dashboard."""
    user_count = count_users()
    trip_count = count_trips()
    top_dests  = get_top_destinations(10)
    all_users  = get_all_users()
    all_trips  = get_all_trips()

    return render_template("admin/dashboard.html",
        user_count=user_count,
        trip_count=trip_count,
        top_destinations=top_dests,
        users=all_users,
        trips=all_trips[:20]
    )


@admin_bp.route("/users")
@login_required
@admin_required
def manage_users():
    """Admin: list all users."""
    users = get_all_users()
    return render_template("admin/users.html", users=users)


@admin_bp.route("/users/<int:user_id>/delete", methods=["POST"])
@login_required
@admin_required
def remove_user(user_id: int):
    """Admin: delete a user."""
    if user_id == session.get("user_id"):
        flash("Cannot delete your own account.", "warning")
    else:
        delete_user(user_id)
        flash("User deleted.", "success")
    return redirect(url_for("admin.manage_users"))


@admin_bp.route("/trips")
@login_required
@admin_required
def manage_trips():
    """Admin: all trips overview."""
    trips = get_all_trips()
    return render_template("admin/trips.html", trips=trips)


@admin_bp.route("/api/analytics")
@login_required
@admin_required
def analytics_api():
    """JSON analytics for admin charts."""
    top_dests = get_top_destinations(10)
    return jsonify({
        "users": count_users(),
        "trips": count_trips(),
        "top_destinations": [dict(d) for d in top_dests]
    })
