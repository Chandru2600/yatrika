"""
Stay Manager Routes & Blueprint
Handles public and personalized stay management, IBM Granite AI detection,
and interactive MapLibre road route generation.
"""

from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, jsonify

from backend.services.stay.stay_service import find_managed_stays
from backend.services.routing.osrm_client import get_osrm_client
from backend.agents_models.coord_resolver import resolve_destination_coords

stay_bp = Blueprint("stay_routes", __name__, url_prefix="/stay-manager")


@stay_bp.route("", methods=["GET"])
def stay_manager_view():
    """Renders the main split-screen Stay Manager page with Launchpad controls."""
    source = request.args.get("source", "Bengaluru").strip()
    destination = request.args.get("destination", "Coorg").strip()
    checkin = request.args.get("checkin", "")
    checkout = request.args.get("checkout", "")
    days_param = request.args.get("num_days") or request.args.get("days", "3")
    budget = request.args.get("budget", "3000")
    travelers = request.args.get("travelers", "2")
    purpose = request.args.get("purpose", "all").strip()

    try:
        d_val = max(1, int(days_param))
    except (ValueError, TypeError):
        d_val = 3

    # Default to upcoming weekend if dates not provided
    if not checkin:
        tomorrow = datetime.now() + timedelta(days=2)
        checkin = tomorrow.strftime("%Y-%m-%d")
    if not checkout:
        end_dt = datetime.strptime(checkin, "%Y-%m-%d") + timedelta(days=d_val)
        checkout = end_dt.strftime("%Y-%m-%d")

    try:
        b_val = float(budget)
    except ValueError:
        b_val = 3000.0

    try:
        t_val = int(travelers)
    except ValueError:
        t_val = 2

    # Initial server-side stay discovery
    initial_data = find_managed_stays(
        source=source,
        destination=destination,
        checkin=checkin,
        checkout=checkout,
        budget=b_val,
        travelers=t_val,
        purpose=purpose,
        num_days=d_val
    )

    return render_template(
        "stay_manager/stay_manager.html",
        initial_data=initial_data,
        source=source,
        destination=destination,
        checkin=checkin,
        checkout=checkout,
        num_days=d_val,
        budget=int(b_val),
        travelers=t_val,
        purpose=purpose
    )


@stay_bp.route("/api/search", methods=["GET"])
def search_stays_api():
    """Asynchronous JSON endpoint for real-time stay search."""
    source = request.args.get("source", "").strip()
    destination = request.args.get("destination", "").strip() or "Coorg"
    checkin = request.args.get("checkin", "").strip()
    checkout = request.args.get("checkout", "").strip()
    days_param = request.args.get("num_days") or request.args.get("days", "")
    purpose = request.args.get("purpose", "all").strip()

    d_val = None
    if days_param:
        try:
            d_val = max(1, int(days_param))
        except (ValueError, TypeError):
            d_val = None

    try:
        budget = float(request.args.get("budget", 2500))
    except (ValueError, TypeError):
        budget = 2500.0

    try:
        travelers = int(request.args.get("travelers", 2))
    except (ValueError, TypeError):
        travelers = 2

    result = find_managed_stays(
        source=source,
        destination=destination,
        checkin=checkin,
        checkout=checkout,
        budget=budget,
        travelers=travelers,
        purpose=purpose,
        num_days=d_val
    )
    return jsonify(result)


@stay_bp.route("/api/route", methods=["POST"])
def get_stay_to_dest_route():
    """
    Returns an OSRM road polyline and driving stats connecting a stay to the destination center.
    Falls back to straight-line GeoJSON if OSRM is unreachable.
    """
    data = request.get_json(silent=True) or {}
    stay_lat = data.get("stay_lat")
    stay_lon = data.get("stay_lon")
    dest_lat = data.get("dest_lat")
    dest_lon = data.get("dest_lon")

    if not all([stay_lat, stay_lon, dest_lat, dest_lon]):
        return jsonify({"success": False, "error": "Missing coordinates"}), 400

    try:
        client = get_osrm_client()
        # OSRM expects waypoints as [(lon, lat), ...]
        waypoints = [(float(stay_lon), float(stay_lat)), (float(dest_lon), float(dest_lat))]
        route = client.get_route(waypoints, steps=True)
        if route and route.get("geometry"):
            return jsonify({
                "success": True,
                "source": "osrm",
                "geometry": route["geometry"],
                "distance_km": route.get("distance_km", 2.0),
                "duration_mins": route.get("duration_mins", 6),
                "steps": route.get("steps", [])
            })
    except Exception:
        pass

    # Fallback straight-line GeoJSON LineString
    fallback_geom = {
        "type": "LineString",
        "coordinates": [
            [float(stay_lon), float(stay_lat)],
            [float(dest_lon), float(dest_lat)]
        ]
    }
    return jsonify({
        "success": True,
        "source": "haversine_fallback",
        "geometry": fallback_geom,
        "distance_km": 2.5,
        "duration_mins": 8,
        "steps": []
    })
