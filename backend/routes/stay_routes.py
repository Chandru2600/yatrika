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


@stay_bp.route("/transport", methods=["GET"])
def stay_transport_view():
    """
    Stay Manager Step 2: Select Mode of Transport (Train, Bus, Flight, Cab/Drive)
    with strictly per-person fares and zero sightseeing/daily schedule clutter.
    """
    source = request.args.get("source", "Bengaluru").strip()
    destination = request.args.get("destination", "Infosys Electronic City, Bengaluru").strip()
    checkin = request.args.get("checkin", "")
    checkout = request.args.get("checkout", "")
    num_days = request.args.get("num_days", "3")
    travelers = request.args.get("travelers", "2")
    budget = request.args.get("budget", "2500")

    stay_info = {
        "id": request.args.get("stay_id", "stay_1"),
        "name": request.args.get("stay_name", "Selected Stay"),
        "price_per_night": request.args.get("stay_price", "2500"),
        "price_per_person_day": request.args.get("stay_pppd", "1250"),
        "lat": request.args.get("stay_lat", ""),
        "lon": request.args.get("stay_lon", ""),
        "img": request.args.get("stay_img", ""),
        "address": request.args.get("stay_address", destination),
        "distance_km": request.args.get("stay_dist", "2.0"),
        "drive_mins": request.args.get("stay_mins", "6"),
    }

    return render_template(
        "stay_manager/stay_transport.html",
        source=source,
        destination=destination,
        checkin=checkin,
        checkout=checkout,
        num_days=num_days,
        travelers=travelers,
        budget=budget,
        stay=stay_info
    )


@stay_bp.route("/summary", methods=["GET"])
def stay_summary_view():
    """
    Stay Manager Step 3: Clean Stay & Transport Summary (no daily schedule/trip jargon)
    plus Recommended Nearby Sights and Alternative Hotels Nearby at the bottom.
    """
    from backend.agents_models.scheduling_model import ItinerarySchedulingModel
    from backend.services.stay.stay_service import _build_booking_links

    source = request.args.get("source", "Bengaluru").strip()
    destination = request.args.get("destination", "Infosys Electronic City, Bengaluru").strip()
    checkin = request.args.get("checkin", "")
    checkout = request.args.get("checkout", "")
    try:
        num_days = max(1, int(request.args.get("num_days", "3")))
    except (ValueError, TypeError):
        num_days = 3
    try:
        travelers = max(1, int(request.args.get("travelers", "2")))
    except (ValueError, TypeError):
        travelers = 2
    try:
        budget = float(request.args.get("budget", "2500"))
    except (ValueError, TypeError):
        budget = 2500.0

    stay_name = request.args.get("stay_name", "Selected Stay")
    stay_price = int(float(request.args.get("stay_price", "2500") or 2500))
    stay_pppd = int(float(request.args.get("stay_pppd", str(round(stay_price / travelers))) or round(stay_price / travelers)))
    stay_lat_raw = request.args.get("stay_lat", "")
    stay_lon_raw = request.args.get("stay_lon", "")

    dest_lat, dest_lon = resolve_destination_coords(destination)
    try:
        s_lat = float(stay_lat_raw) if stay_lat_raw else dest_lat
        s_lon = float(stay_lon_raw) if stay_lon_raw else dest_lon
    except ValueError:
        s_lat, s_lon = dest_lat, dest_lon

    stay_info = {
        "id": request.args.get("stay_id", "stay_1"),
        "name": stay_name,
        "price_per_night": stay_price,
        "price_per_person_day": stay_pppd,
        "lat": s_lat,
        "lon": s_lon,
        "img": request.args.get("stay_img", "") or "https://images.unsplash.com/photo-1566073771259-6a8506099945?auto=format&fit=crop&w=800&q=80",
        "address": request.args.get("stay_address", destination),
        "distance_km": request.args.get("stay_dist", "2.0"),
        "drive_mins": request.args.get("stay_mins", "6"),
        "booking_links": _build_booking_links(stay_name, destination, checkin, checkout, travelers)
    }

    transit_info = {
        "mode": request.args.get("transit_mode", "train").upper(),
        "title": request.args.get("transit_title", "Selected Transport"),
        "fare_per_person": int(float(request.args.get("transit_fare", "850") or 850)),
        "departure": request.args.get("transit_dep", "06:30"),
        "arrival": request.args.get("transit_arr", "12:15"),
        "duration": request.args.get("transit_dur", "5h 45m"),
        "details": request.args.get("transit_details", "Verified Inter-City Transfer"),
    }

    # 1. Fetch Recommended Alternative Hotels Nearby
    nearby_stays = []
    try:
        stays_res = find_managed_stays(
            source=source,
            destination=destination,
            checkin=checkin,
            checkout=checkout,
            budget=budget,
            travelers=travelers,
            purpose="work",
            num_days=num_days
        )
        for st in stays_res.get("stays", []):
            if st.get("name", "").lower() != stay_name.lower():
                nearby_stays.append(st)
            if len(nearby_stays) >= 4:
                break
    except Exception:
        nearby_stays = []

    # 2. Fetch Recommended Nearby Sights & Places STRICTLY Inside the Same City
    nearby_sights = []
    try:
        city_query = destination.split(",")[-1].strip() if "," in destination else destination
        city_lower = city_query.lower()
        city_aliases = {city_lower}
        if "bengaluru" in city_lower or "bangalore" in city_lower:
            city_aliases.update({"bengaluru", "bangalore"})
        elif "mumbai" in city_lower or "bombay" in city_lower:
            city_aliases.update({"mumbai", "bombay"})
        elif "gurugram" in city_lower or "gurgaon" in city_lower:
            city_aliases.update({"gurugram", "gurgaon", "delhi", "ncr"})

        sched_model = ItinerarySchedulingModel()
        raw_sights = sched_model.fetch_attractions(city_query, stay_coords=(s_lat, s_lon))
        if not raw_sights and city_query != destination:
            raw_sights = sched_model.fetch_attractions(destination, stay_coords=(s_lat, s_lon))

        in_city_sights = []
        for sg in (raw_sights or []):
            sg_name = str(sg.get("name", "")).strip()
            sg_low = sg_name.lower()
            if any(noise in sg_low for noise in ["gate ", "circle memorial", "bus stand", "signal", "toll"]):
                continue
            sg_dist = float(sg.get("dist") or sg.get("distance_km") or 99.0)
            sg_city = str(sg.get("city", "")).lower()
            is_same_city = any(alias in sg_city for alias in city_aliases)
            # Strictly keep places inside the city (<= 20 km or exact city match within 22 km)
            if sg_dist <= 20.0 or (is_same_city and sg_dist <= 22.0):
                cat_lbl = str(sg.get("category") or sg.get("cat") or "Sightseeing")
                sg["best_time"] = "Morning / Weekend" if "nature" in cat_lbl.lower() or "park" in cat_lbl.lower() else "Evening / Post-work"
                lat_v = sg.get("lat") or sg.get("latitude") or s_lat
                lon_v = sg.get("lon") or sg.get("longitude") or s_lon
                sg["maps_url"] = f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(sg_name)}%20@{lat_v},{lon_v}" if False else f"https://www.google.com/maps/search/?api=1&query={lat_v},{lon_v}"
                in_city_sights.append(sg)

        # Sort closest to the stay/office first, then highest rating
        in_city_sights.sort(key=lambda x: (float(x.get("dist") or 99.0), -float(x.get("rating") or 4.0)))

        # Enforce category diversity (max 2 per category so parks/lakes/landmarks/museums appear alongside temples)
        diverse_sights = []
        cat_counts = {}
        overflow_sights = []
        for sg in in_city_sights:
            c_key = str(sg.get("category") or sg.get("cat") or "Other").lower()
            if cat_counts.get(c_key, 0) < 2:
                diverse_sights.append(sg)
                cat_counts[c_key] = cat_counts.get(c_key, 0) + 1
            else:
                overflow_sights.append(sg)
            if len(diverse_sights) >= 6:
                break
        if len(diverse_sights) < 6:
            diverse_sights.extend(overflow_sights[:6 - len(diverse_sights)])

        nearby_sights = diverse_sights[:6]
    except Exception:
        nearby_sights = []

    return render_template(
        "stay_manager/stay_summary.html",
        source=source,
        destination=destination,
        checkin=checkin,
        checkout=checkout,
        num_days=num_days,
        travelers=travelers,
        budget=int(budget),
        stay=stay_info,
        transit=transit_info,
        nearby_stays=nearby_stays,
        nearby_sights=nearby_sights
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
