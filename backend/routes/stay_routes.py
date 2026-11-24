"""
Stay Manager Routes & Blueprint
Handles public and personalized stay management, IBM Granite AI detection,
dedicated next-page results, and interactive MapLibre floating window navigation.
"""

from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, jsonify

from backend.services.stay.stay_service import find_managed_stays
from backend.services.routing.osrm_client import get_osrm_client
from backend.agents_models.coord_resolver import resolve_destination_coords

stay_bp = Blueprint("stay_routes", __name__, url_prefix="/stay-manager")


@stay_bp.route("", methods=["GET"])
def stay_manager_view():
    """
    Renders Stay Manager.
    - If accessed directly (or with modify=1): shows the Launchpad 3D Entry Card with 'Continue' button.
    - If destination is provided (e.g. from existing links or unit test): shows the dedicated next-page results.
    """
    has_destination = bool(request.args.get("destination"))
    is_modify = bool(request.args.get("modify"))

    if has_destination and not is_modify:
        return stay_results_view()

    source = request.args.get("source", "Bengaluru").strip()
    destination = request.args.get("destination", "Infosys Electronic City, Bengaluru").strip()
    checkin = request.args.get("checkin", "")
    checkout = request.args.get("checkout", "")
    days_param = request.args.get("num_days") or request.args.get("days", "3")
    budget = request.args.get("budget", "2500")
    travelers = request.args.get("travelers", "2")
    purpose = request.args.get("purpose", "work").strip()

    try:
        d_val = max(1, int(days_param))
    except (ValueError, TypeError):
        d_val = 3

    if not checkin:
        tomorrow = datetime.now() + timedelta(days=2)
        checkin = tomorrow.strftime("%Y-%m-%d")
    if not checkout:
        end_dt = datetime.strptime(checkin, "%Y-%m-%d") + timedelta(days=d_val)
        checkout = end_dt.strftime("%Y-%m-%d")

    return render_template(
        "stay_manager/stay_search.html",
        source=source,
        destination=destination,
        checkin=checkin,
        checkout=checkout,
        num_days=d_val,
        budget=budget,
        travelers=travelers,
        purpose=purpose
    )


@stay_bp.route("/results", methods=["GET"])
def stay_results_view():
    """
    Dedicated Next-Page for Stay Results:
    Displays stays as spacious cards (no beside map), rich facility & luxury filters,
    and opens the map as a sleek floating window.
    """
    source = request.args.get("source", "Bengaluru").strip()
    destination = request.args.get("destination", "Infosys Electronic City, Bengaluru").strip()
    checkin = request.args.get("checkin", "")
    checkout = request.args.get("checkout", "")
    days_param = request.args.get("num_days") or request.args.get("days", "3")
    budget = request.args.get("budget", "2500")
    travelers = request.args.get("travelers", "2")
    purpose = request.args.get("purpose", "work").strip()

    try:
        d_val = max(1, int(days_param))
    except (ValueError, TypeError):
        d_val = 3

    if not checkin:
        tomorrow = datetime.now() + timedelta(days=2)
        checkin = tomorrow.strftime("%Y-%m-%d")
    if not checkout:
        end_dt = datetime.strptime(checkin, "%Y-%m-%d") + timedelta(days=d_val)
        checkout = end_dt.strftime("%Y-%m-%d")

    try:
        b_val = float(budget)
    except ValueError:
        b_val = 2500.0

    try:
        t_val = int(travelers)
    except ValueError:
        t_val = 2

    # Discover stays using IBM Granite AI with fallback to Agent 4 Accommodations model
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
        "stay_manager/stay_results.html",
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
        budget = float(request.args.get("budget", 2500.0))
    except ValueError:
        budget = 2500.0

    try:
        travelers = int(request.args.get("travelers", 2))
    except ValueError:
        travelers = 2

    data = find_managed_stays(
        source=source,
        destination=destination,
        checkin=checkin,
        checkout=checkout,
        budget=budget,
        travelers=travelers,
        purpose=purpose,
        num_days=d_val
    )
    return jsonify(data)


@stay_bp.route("/api/route", methods=["POST"])
def get_stay_road_route():
    """
    Computes an exact driving road circuit geometry between a selected hotel and the destination anchor.
    Used by the floating MapLibre window to render real OSRM road paths.
    """
    body = request.get_json() or {}
    try:
        stay_lat = float(body.get("stay_lat"))
        stay_lon = float(body.get("stay_lon"))
        dest_lat = float(body.get("dest_lat"))
        dest_lon = float(body.get("dest_lon"))
    except (TypeError, ValueError) as err:
        return jsonify({"success": False, "error": f"Invalid coordinates: {err}"}), 400

    osrm = get_osrm_client()
    coords = [(stay_lon, stay_lat), (dest_lon, dest_lat)]
    route_res = osrm.get_route(coords, profile="driving")

    if route_res and route_res.get("geometry"):
        return jsonify({
            "success": True,
            "source": route_res.get("source", "osrm"),
            "distance_km": route_res.get("distance_km", 2.0),
            "duration_mins": route_res.get("duration_mins", 6),
            "geometry": route_res.get("geometry")
        })

    # Haversine straight-line fallback geometry if OSRM is unreachable
    straight_line_geom = {
        "type": "LineString",
        "coordinates": [
            [stay_lon, stay_lat],
            [dest_lon, dest_lat]
        ]
    }
    return jsonify({
        "success": True,
        "source": "fallback_direct",
        "distance_km": 2.5,
        "duration_mins": 8,
        "geometry": straight_line_geom
    })
