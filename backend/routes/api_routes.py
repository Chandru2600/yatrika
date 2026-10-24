"""
TravelPlannerAgent - REST API Routes (Blueprint)
"""

import json
from datetime import date, datetime
from functools import wraps
from flask import Blueprint, request, jsonify, current_app, send_file
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature

# Models
from backend.models.user import (
    create_user, get_user_by_email, verify_password,
    update_last_login, get_user_by_id, get_all_users, delete_user, count_users
)
from backend.models.trip import (
    create_trip, get_trip_by_id, get_trips_by_user,
    update_trip_itinerary, delete_trip, save_trip,
    get_saved_trips, unsave_trip, add_expense, get_expenses,
    get_all_trips, count_trips, get_top_destinations
)

# Services
from backend.services.granite.granite_service import generate_complete_travel_plan
from backend.services.weather.weather_service import (
    get_current_weather, get_forecast, get_travel_weather_advice
)
from backend.services.pdf.pdf_service import generate_trip_pdf

api_bp = Blueprint("api", __name__, url_prefix="/api")


# ── Token Helpers & Decorators ─────────────────────────────────

def generate_auth_token(user_id: int) -> str:
    """Generate a signed auth token valid for 30 days."""
    serializer = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
    return serializer.dumps(user_id, salt="api-auth")


def verify_auth_token(token: str):
    """Verify signed auth token and return user_id or None."""
    serializer = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
    try:
        user_id = serializer.loads(token, salt="api-auth", max_age=86400 * 30)
        return user_id
    except (SignatureExpired, BadSignature):
        return None


def api_login_required(f):
    """Decorator to require token authentication on API routes."""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return jsonify({"error": "Missing or invalid token"}), 401
        
        token = auth_header.split(" ")[1]
        user_id = verify_auth_token(token)
        if not user_id:
            return jsonify({"error": "Token expired or invalid"}), 401
        
        request.user_id = user_id
        return f(*args, **kwargs)
    return decorated


def api_admin_required(f):
    """Decorator to require admin role on API routes."""
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_user_by_id(request.user_id)
        if not user or user["role"] != "admin":
            return jsonify({"error": "Admin access required"}), 403
        request.user = user
        return f(*args, **kwargs)
    return decorated


def row_to_dict(row):
    """Convert an sqlite3.Row object to a clean Python dictionary."""
    if row is None:
        return None
    return dict(row)


def rows_to_list(rows):
    """Convert a list of sqlite3.Row objects to Python dictionaries."""
    return [row_to_dict(r) for r in rows]


# ── Auth Endpoints ─────────────────────────────────────────────

@api_bp.route("/auth/register", methods=["POST"])
def register():
    """Register a new user and login."""
    data = request.get_json() or {}
    name     = data.get("name", "").strip()
    email    = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not name or not email or not password:
        return jsonify({"error": "All fields (name, email, password) are required."}), 400

    if len(password) < 8:
        return jsonify({"error": "Password must be at least 8 characters long."}), 400

    if get_user_by_email(email):
        return jsonify({"error": "Email is already registered. Please login."}), 400

    try:
        user_id = create_user(name, email, password)
        token = generate_auth_token(user_id)
        user = get_user_by_id(user_id)
        return jsonify({
            "success": True,
            "token": token,
            "user": {
                "id": user["id"],
                "name": user["name"],
                "email": user["email"],
                "role": user["role"]
            }
        }), 201
    except Exception as e:
        return jsonify({"error": f"Registration failed: {str(e)}"}), 500


@api_bp.route("/auth/login", methods=["POST"])
def login():
    """Authenticate credentials and return a token."""
    data = request.get_json() or {}
    email    = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({"error": "Email and password are required."}), 400

    user = get_user_by_email(email)
    if user and verify_password(password, user["password"]):
        update_last_login(user["id"])
        token = generate_auth_token(user["id"])
        return jsonify({
            "success": True,
            "token": token,
            "user": {
                "id": user["id"],
                "name": user["name"],
                "email": user["email"],
                "role": user["role"]
            }
        })
    else:
        return jsonify({"error": "Invalid email or password."}), 401


@api_bp.route("/auth/profile", methods=["GET"])
@api_login_required
def profile():
    """Get the authenticated user's profile."""
    user = get_user_by_id(request.user_id)
    if not user:
        return jsonify({"error": "User not found."}), 404
    return jsonify({
        "id": user["id"],
        "name": user["name"],
        "email": user["email"],
        "role": user["role"],
        "created_at": user["created_at"],
        "last_login": user["last_login"]
    })


# ── Trip Endpoints ─────────────────────────────────────────────

@api_bp.route("/trips", methods=["GET"])
@api_login_required
def get_trips():
    """Get all trips for the authenticated user."""
    trips = get_trips_by_user(request.user_id)
    return jsonify(rows_to_list(trips))


@api_bp.route("/trips", methods=["POST"])
@api_login_required
def create_new_trip():
    """Generate a new AI travel plan and save it to the DB."""
    data = request.get_json() or {}
    destination   = data.get("destination", "").strip()
    start_date    = data.get("start_date")
    end_date      = data.get("end_date")
    num_days      = int(data.get("num_days", 1))
    budget        = float(data.get("budget", 1000))
    num_travelers = int(data.get("num_travelers", 1))
    travel_style  = data.get("travel_style", "budget")
    transport     = data.get("transport", "flight")
    interests     = data.get("interests", [])
    special_reqs  = data.get("special_requirements", [])

    if not destination:
        return jsonify({"error": "Destination is required."}), 400

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

    try:
        # Create initial record (status = draft)
        trip_id = create_trip(request.user_id, trip_data)

        # Call Travel Planner Agent Engine
        try:
            ai_result = generate_complete_travel_plan(trip_data)
        except Exception as e:
            ai_result = {
                "itinerary": {"error": str(e)},
                "budget":    {}, "hotels": {}, "transport": {}, "food": {}
            }

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

        return jsonify({
            "success": True,
            "trip_id": trip_id
        }), 201

    except Exception as e:
        return jsonify({"error": f"Failed to create trip: {str(e)}"}), 500


@api_bp.route("/trips/<int:trip_id>", methods=["GET"])
@api_login_required
def get_trip_details(trip_id: int):
    """Retrieve full trip information including parsed JSON configurations."""
    trip = get_trip_by_id(trip_id)
    if not trip or trip["user_id"] != request.user_id:
        return jsonify({"error": "Trip not found or access denied."}), 404

    try:
        itinerary = json.loads(trip["itinerary_json"] or "{}")
        weather   = json.loads(trip["weather_json"]   or "{}")
        budget    = json.loads(trip["budget_json"]    or "{}")
        hotels    = json.loads(trip["hotels_json"]    or "{}")
    except Exception:
        itinerary, weather, budget, hotels = {}, {}, {}, {}

    expenses = get_expenses(trip_id)

    return jsonify({
        "trip": row_to_dict(trip),
        "itinerary": itinerary,
        "weather": weather,
        "budget": budget,
        "hotels": hotels,
        "expenses": rows_to_list(expenses)
    })


@api_bp.route("/trips/<int:trip_id>", methods=["DELETE"])
@api_login_required
def delete_trip_api(trip_id: int):
    """Delete a trip."""
    trip = get_trip_by_id(trip_id)
    if not trip or trip["user_id"] != request.user_id:
        return jsonify({"error": "Trip not found or access denied."}), 404

    delete_trip(trip_id, request.user_id)
    return jsonify({"success": True, "message": "Trip deleted."})


@api_bp.route("/trips/<int:trip_id>/save", methods=["POST"])
@api_login_required
def save_trip_api(trip_id: int):
    """Save/favorite a trip."""
    trip = get_trip_by_id(trip_id)
    if not trip or trip["user_id"] != request.user_id:
        return jsonify({"error": "Trip not found or access denied."}), 404

    data = request.get_json() or {}
    notes = data.get("notes", "")
    
    # Check if already saved to avoid duplicates
    saved = get_saved_trips(request.user_id)
    if any(item["trip_id"] == trip_id for item in saved):
        return jsonify({"success": True, "message": "Trip is already saved."})

    save_trip(request.user_id, trip_id, notes)
    return jsonify({"success": True, "message": "Trip saved to favorites."})


@api_bp.route("/saved-trips", methods=["GET"])
@api_login_required
def get_saved():
    """Retrieve all user saved/favorited trips."""
    saved = get_saved_trips(request.user_id)
    return jsonify(rows_to_list(saved))


@api_bp.route("/saved-trips/<int:saved_id>", methods=["DELETE"])
@api_login_required
def remove_saved_api(saved_id: int):
    """Unsave/remove a favorite trip using its saved_trips ID."""
    # Note: unsave_trip checks user_id inside models
    unsave_trip(saved_id, request.user_id)
    return jsonify({"success": True, "message": "Removed from saved trips."})


@api_bp.route("/trips/<int:trip_id>/expenses", methods=["POST"])
@api_login_required
def add_expense_api(trip_id: int):
    """Log an actual expense against a trip."""
    trip = get_trip_by_id(trip_id)
    if not trip or trip["user_id"] != request.user_id:
        return jsonify({"error": "Trip not found or access denied."}), 404

    data = request.get_json() or {}
    category    = data.get("category", "miscellaneous")
    amount      = float(data.get("amount", 0))
    description = data.get("description", "")

    if amount <= 0:
        return jsonify({"error": "Amount must be greater than zero."}), 400

    add_expense(trip_id, category, amount, description)
    return jsonify({"success": True, "message": "Expense logged successfully."})


@api_bp.route("/trips/<int:trip_id>/pdf", methods=["GET"])
@api_login_required
def get_trip_pdf_api(trip_id: int):
    """Generate and serve the PDF report for a trip."""
    trip = get_trip_by_id(trip_id)
    if not trip or trip["user_id"] != request.user_id:
        return jsonify({"error": "Trip not found or access denied."}), 404

    try:
        itinerary = json.loads(trip["itinerary_json"] or "{}")
        budget    = json.loads(trip["budget_json"]    or "{}")
        hotels    = json.loads(trip["hotels_json"]    or "{}")
        weather   = json.loads(trip["weather_json"]   or "{}")
    except Exception:
        return jsonify({"error": "Trip data is incomplete, cannot generate PDF."}), 400

    try:
        pdf_path = generate_trip_pdf(trip, itinerary, budget, hotels, weather)
        return send_file(
            pdf_path,
            as_attachment=True,
            download_name=f"TravelPlan_{trip['destination'].replace(' ', '_')}.pdf",
            mimetype="application/pdf"
        )
    except Exception as e:
        return jsonify({"error": f"PDF generation failed: {str(e)}"}), 500


# ── Admin Endpoints ────────────────────────────────────────────

@api_bp.route("/admin/analytics", methods=["GET"])
@api_login_required
@api_admin_required
def get_admin_analytics():
    """Retrieve global platform user and trip stats."""
    top_dests = get_top_destinations(10)
    return jsonify({
        "users": count_users(),
        "trips": count_trips(),
        "top_destinations": [dict(d) for d in top_dests]
    })


@api_bp.route("/admin/users", methods=["GET"])
@api_login_required
@api_admin_required
def get_admin_users():
    """List all platform users."""
    users = get_all_users()
    return jsonify(rows_to_list(users))


@api_bp.route("/admin/users/<int:user_id>", methods=["DELETE"])
@api_login_required
@api_admin_required
def delete_admin_user(user_id: int):
    """Delete a user account from the system."""
    if user_id == request.user_id:
        return jsonify({"error": "Cannot delete your own administrator account."}), 400
        
    delete_user(user_id)
    return jsonify({"success": True, "message": "User account successfully deleted."})
