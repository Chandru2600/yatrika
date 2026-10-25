"""
TravelPlannerAgent - Trip Model
"""

import json
import secrets
from backend.database.db import execute_query, execute_insert


def create_trip(user_id: int, data: dict) -> int:
    """Insert a new trip and return its ID."""
    transit_details = data.get("transit_details", {})
    transit_details_str = json.dumps(transit_details) if isinstance(transit_details, (dict, list)) else str(transit_details or "")
    share_token = data.get("share_token") or secrets.token_urlsafe(16)
    is_public = 1 if data.get("is_public") else 0

    return execute_insert("""
        INSERT INTO trips
            (user_id, destination, start_date, end_date, num_days, budget,
             num_travelers, travel_style, transport, transit_mode, transit_cost,
             arrival_time, transit_details_json, interests,
             special_requirements, status, share_token, is_public)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'draft', ?, ?)
    """, (
        user_id,
        data.get("destination"),
        data.get("start_date"),
        data.get("end_date"),
        data.get("num_days", 1),
        data.get("budget", 0),
        data.get("num_travelers", 1),
        data.get("travel_style", "budget"),
        data.get("transport", "flight"),
        data.get("transit_mode", data.get("transport", "car")),
        float(data.get("transit_cost", 0)),
        data.get("arrival_time", "10:00"),
        transit_details_str,
        json.dumps(data.get("interests", [])),
        json.dumps(data.get("special_requirements", [])),
        share_token,
        is_public
    ))



def get_trip_by_id(trip_id: int):
    """Fetch a trip by primary key."""
    return execute_query(
        "SELECT * FROM trips WHERE id = ?",
        (trip_id,),
        fetchone=True
    )


def get_trips_by_user(user_id: int):
    """Return all trips for a user, newest first."""
    return execute_query(
        "SELECT * FROM trips WHERE user_id = ? ORDER BY created_at DESC",
        (user_id,)
    )


def update_trip_itinerary(trip_id: int, itinerary: dict, weather: dict,
                          budget: dict, hotels: dict) -> None:
    """Persist AI-generated results back into the trip row."""
    execute_query("""
        UPDATE trips
        SET itinerary_json = ?,
            weather_json   = ?,
            budget_json    = ?,
            hotels_json    = ?,
            status         = 'completed',
            updated_at     = datetime('now')
        WHERE id = ?
    """, (
        json.dumps(itinerary),
        json.dumps(weather),
        json.dumps(budget),
        json.dumps(hotels),
        trip_id
    ))


def delete_trip(trip_id: int, user_id: int) -> None:
    """Delete a trip owned by user."""
    execute_query(
        "DELETE FROM trips WHERE id = ? AND user_id = ?",
        (trip_id, user_id)
    )


def save_trip(user_id: int, trip_id: int, notes: str = "") -> int:
    """Save a trip for later reference."""
    return execute_insert(
        "INSERT INTO saved_trips (user_id, trip_id, notes) VALUES (?, ?, ?)",
        (user_id, trip_id, notes)
    )


def get_saved_trips(user_id: int):
    """Return all saved trips with trip info."""
    return execute_query("""
        SELECT st.id as saved_id, st.saved_at, st.notes,
               t.id as trip_id, t.destination, t.start_date, t.end_date,
               t.budget, t.status, t.travel_style
        FROM saved_trips st
        JOIN trips t ON t.id = st.trip_id
        WHERE st.user_id = ?
        ORDER BY st.saved_at DESC
    """, (user_id,))


def unsave_trip(saved_id: int, user_id: int) -> None:
    """Remove a saved trip."""
    execute_query(
        "DELETE FROM saved_trips WHERE id = ? AND user_id = ?",
        (saved_id, user_id)
    )


def get_all_trips():
    """Return all trips for admin view."""
    return execute_query("""
        SELECT t.*, u.name as user_name, u.email as user_email
        FROM trips t
        JOIN users u ON u.id = t.user_id
        ORDER BY t.created_at DESC
    """)


def count_trips() -> int:
    """Return total trip count."""
    row = execute_query("SELECT COUNT(*) as cnt FROM trips", fetchone=True)
    return row["cnt"] if row else 0


def get_top_destinations(limit: int = 10):
    """Return most planned destinations."""
    return execute_query("""
        SELECT destination, COUNT(*) as count
        FROM trips
        GROUP BY destination
        ORDER BY count DESC
        LIMIT ?
    """, (limit,))


def add_expense(trip_id: int, category: str, amount: float, description: str) -> int:
    """Log an expense for a trip."""
    return execute_insert(
        "INSERT INTO expenses (trip_id, category, amount, description) VALUES (?, ?, ?, ?)",
        (trip_id, category, amount, description)
    )


def get_expenses(trip_id: int):
    """Fetch all expenses for a trip."""
    return execute_query(
        "SELECT * FROM expenses WHERE trip_id = ? ORDER BY date",
        (trip_id,)
    )


def delete_expense(expense_id: int, trip_id: int) -> None:
    """Delete an expense record from a trip."""
    execute_query(
        "DELETE FROM expenses WHERE id = ? AND trip_id = ?",
        (expense_id, trip_id)
    )


def get_trip_by_share_token(token: str):
    """Fetch an actively shared trip by its cryptographic token."""
    if not token or not isinstance(token, str) or len(token.strip()) < 10:
        return None
    return execute_query(
        "SELECT * FROM trips WHERE share_token = ? AND is_public = 1",
        (token.strip(),),
        fetchone=True
    )


def enable_trip_sharing(trip_id: int, user_id: int) -> str:
    """Make trip publicly accessible via a secure cryptographic token and return token."""
    trip = get_trip_by_id(trip_id)
    if not trip or trip["user_id"] != user_id:
        return None
    token = trip["share_token"]
    if not token:
        token = secrets.token_urlsafe(16)
    execute_query(
        "UPDATE trips SET is_public = 1, share_token = ? WHERE id = ? AND user_id = ?",
        (token, trip_id, user_id)
    )
    return token


def disable_trip_sharing(trip_id: int, user_id: int) -> bool:
    """Revoke public access for a trip."""
    trip = get_trip_by_id(trip_id)
    if not trip or trip["user_id"] != user_id:
        return False
    execute_query(
        "UPDATE trips SET is_public = 0 WHERE id = ? AND user_id = ?",
        (trip_id, user_id)
    )
    return True


def get_trip_checklist(trip_id: int, user_id: int):
    """Retrieve saved packing checklist for a trip with user ownership verification."""
    trip = get_trip_by_id(trip_id)
    if not trip or trip["user_id"] != user_id:
        return None
    try:
        raw = trip["checklist_json"] if "checklist_json" in trip.keys() else None
        if not raw:
            return None
        return json.loads(raw)
    except Exception:
        return None


def update_trip_checklist(trip_id: int, user_id: int, checklist: dict) -> bool:
    """Persist packing checklist state with strict trip ownership validation."""
    trip = get_trip_by_id(trip_id)
    if not trip or trip["user_id"] != user_id:
        return False
    checklist_str = json.dumps(checklist) if checklist is not None else None
    execute_query(
        "UPDATE trips SET checklist_json = ?, updated_at = datetime('now') WHERE id = ? AND user_id = ?",
        (checklist_str, trip_id, user_id)
    )
    return True

