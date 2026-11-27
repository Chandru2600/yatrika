"""
Single Source of Truth for Yatrika Timeline Coverage & Trip Totals.
Used by Stage 4, Map Header/Day Footers, Finalize, Saved Dossier (/planner/<id>),
PDF export, and WhatsApp share.
"""

from __future__ import annotations

from datetime import datetime, timedelta
import math
import re
import requests

OSRM_ROUTE_URL = "http://router.project-osrm.org/route/v1/driving"
_PAIR_CACHE: dict[tuple[float, float, float, float], tuple[float, int]] = {}


def _fmt_time(total_mins: int) -> str:
    m = int(round(total_mins))
    day_offset = m // (24 * 60)
    m_mod = m % (24 * 60)
    hh = m_mod // 60
    mm = m_mod % 60
    base = f"{hh:02d}:{mm:02d}"
    if day_offset > 0:
        return f"{base} (+{day_offset} day)"
    return base


def _fmt_duration(mins: int) -> str:
    mins = max(0, int(round(mins)))
    h, m = divmod(mins, 60)
    if h and m:
        return f"{h}h {m}m"
    if h:
        return f"{h}h"
    return f"{m}m"


def _parse_time_to_mins(val: str | None, default_mins: int = 360) -> int:
    if not val:
        return default_mins
    s = str(val).strip().upper()
    m = re.search(r"(\d{1,2}):(\d{2})\s*(AM|PM)?", s)
    if not m:
        return default_mins
    hh = int(m.group(1))
    mm = int(m.group(2))
    ampm = m.group(3)
    if ampm == "PM" and hh < 12:
        hh += 12
    elif ampm == "AM" and hh == 12:
        hh = 0
    return hh * 60 + mm


def _parse_duration_mins(val, default_mins: int = 120) -> int:
    if isinstance(val, (int, float)):
        v = float(val)
        # Heuristic: <= 15 is likely hours when passed as float from transit, unless >= 15 mins
        return max(5, int(round(v)))
    if not val:
        return default_mins
    s = str(val).strip().lower()
    total = 0
    hm = re.search(r"(\d+(?:\.\d+)?)\s*h", s)
    mm = re.search(r"(\d+)\s*m", s)
    if hm:
        total += int(round(float(hm.group(1)) * 60))
    if mm:
        total += int(mm.group(1))
    if total > 0:
        return total
    try:
        return max(5, int(round(float(s))))
    except ValueError:
        return default_mins


def _parse_closing_mins(opening: str | None, default_close: int = 18 * 60 + 30) -> int:
    if not opening:
        return default_close
    matches = re.findall(r"(\d{1,2}:\d{2}\s*(?:AM|PM)?)", str(opening), re.IGNORECASE)
    if len(matches) >= 2:
        return _parse_time_to_mins(matches[-1], default_close)
    return default_close


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return 6371.0 * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _osrm_leg(p1: tuple[float, float] | None, p2: tuple[float, float] | None, fallback_km: float = 12.0) -> tuple[float, int]:
    """Return exact (distance_km, duration_mins) between two points using OSRM with pair cache."""
    if not p1 or not p2 or None in p1 or None in p2:
        km = max(1.0, round(float(fallback_km or 12.0), 1))
        mins = max(8, int(round((km / 35.0) * 60)))
        return km, mins

    key = (round(float(p1[0]), 4), round(float(p1[1]), 4), round(float(p2[0]), 4), round(float(p2[1]), 4))
    if key in _PAIR_CACHE:
        return _PAIR_CACHE[key]

    if key[0] == key[2] and key[1] == key[3]:
        _PAIR_CACHE[key] = (0.0, 0)
        return (0.0, 0)

    try:
        url = f"{OSRM_ROUTE_URL}/{key[1]},{key[0]};{key[3]},{key[2]}?overview=false"
        resp = requests.get(url, timeout=4)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("code") == "Ok" and data.get("routes"):
                r = data["routes"][0]
                km = round(r["distance"] / 1000.0, 1)
                mins = max(5, int(round(r["duration"] / 60.0)))
                _PAIR_CACHE[key] = (km, mins)
                return km, mins
    except Exception:
        pass

    air = _haversine_km(key[0], key[1], key[2], key[3])
    km = max(1.0, round(air * 1.35, 1))
    mins = max(8, int(round((km / 38.0) * 60)))
    _PAIR_CACHE[key] = (km, mins)
    return km, mins


def calculate_trip_total(trip: dict) -> dict:
    """Single source of truth for trip money totals across Stages 1-4, Finalize, Dossier & WhatsApp."""
    num_days = max(1, int(trip.get("num_days") or trip.get("days") or 3))
    arr_day_offset = int(trip.get("_arr_day_offset") or 0)
    nights = max(1, num_days - 1 - arr_day_offset) if num_days > 1 else 1
    travelers = max(1, int(trip.get("num_travelers") or trip.get("travelers") or 1))
    budget_target = float(trip.get("budget") or 15000)

    stay = trip.get("stay") or trip.get("selected_stay") or {}
    stay_ppn = float(stay.get("price_per_night") or trip.get("stay_price_per_night") or 0)
    stay_total_group = round(stay_ppn * nights)
    stay_pp = round(stay_total_group / travelers) if stay_total_group > 0 else 0

    transit = trip.get("transit") or {}
    transit_pp = round(float(transit.get("fare_per_person") or trip.get("transit_cost_per_person") or 0))
    transit_group = transit_pp * travelers

    sights = trip.get("selected_attractions") or []
    entry_pp = 0
    _hampi_combo_charged = False
    _HAMPI_ASI_COMBO = ("vittala", "vijaya vittala", "lotus mahal", "elephant stables", "horse stables")
    for s in sights:
        s_low = (s.get("name") or "").lower()
        if s_low.strip() in ("hanging bridge", "bridge"):
            continue
        fee = int(float(s.get("fee") or 0))
        if any(k in s_low for k in _HAMPI_ASI_COMBO):
            if not _hampi_combo_charged:
                entry_pp += 40
                _hampi_combo_charged = True
        else:
            entry_pp += fee
    entry_group = entry_pp * travelers

    food_pp = 600 * num_days
    food_group = food_pp * travelers

    misc_pp = 500
    misc_group = misc_pp * travelers

    per_person_total = stay_pp + transit_pp + entry_pp + food_pp + misc_pp
    group_total = stay_total_group + transit_group + entry_group + food_group + misc_group
    is_over_target = group_total > budget_target
    if is_over_target:
        verdict = (
            f"The selected mode of transport is NOT possible on this ₹{round(budget_target):,} budget "
            f"(estimated total: ₹{group_total:,})."
        )
        verdict_options = [
            f"(a) Increase budget to ₹{group_total:,}",
            "(b) Switch to Train/Bus for lower transit cost with longer travel time",
        ]
    else:
        verdict = (
            f"Fits within ₹{round(budget_target):,} budget "
            f"(estimated total: ₹{group_total:,}; remaining buffer: ₹{round(budget_target) - group_total:,})."
        )
        verdict_options = []

    return {
        "num_days": num_days,
        "nights": nights,
        "travelers": travelers,
        "stay_per_person": stay_pp,
        "stay_group": stay_total_group,
        "transit_per_person": transit_pp,
        "transit_group": transit_group,
        "entry_per_person": entry_pp,
        "entry_group": entry_group,
        "food_per_person": food_pp,
        "food_group": food_group,
        "misc_per_person": misc_pp,
        "misc_group": misc_group,
        "per_person_total": per_person_total,
        "group_total": group_total,
        "budget_target": round(budget_target),
        "is_over_target": is_over_target,
        "budget_status_label": "Over Target" if is_over_target else "Under Target",
        "budget_verdict": verdict,
        "budget_verdict_options": verdict_options,
    }


def _fill_gap_if_needed(events: list[dict], from_mins: int, to_mins: int, hotel_name: str) -> None:
    gap = to_mins - from_mins
    if gap > 30:
        events.append({
            "start_time": _fmt_time(from_mins),
            "end_time": _fmt_time(to_mins),
            "duration_mins": gap,
            "duration_label": _fmt_duration(gap),
            "distance_km": 0.0,
            "distance_label": "",
            "mode": "leisure",
            "type": "leisure",
            "icon": "☕",
            "from_place": hotel_name,
            "to_place": hotel_name,
            "title": "Free time / rest at hotel",
            "subtitle": f"Relax & recharge at {hotel_name} ({_fmt_time(from_mins)}–{_fmt_time(to_mins)} · {_fmt_duration(gap)})",
        })


def build_timeline(trip: dict) -> dict:
    """
    Build the single authoritative timeline object for the entire trip.
    Every leg has start_time, end_time, duration_mins, distance_km, distance_label,
    mode, from_place, to_place, title, and subtitle. No unlabeled gap > 30 min.
    """
    source = (trip.get("source") or "Bengaluru").split(",")[0].strip()
    destination = (trip.get("destination") or "Coorg").split(",")[0].strip()
    num_days = max(1, int(trip.get("num_days") or trip.get("days") or 3))

    # Dates: NEVER invent 2026-12-02 or any other default date
    start_date_str = (trip.get("start_date") or "").strip()
    end_date_str = (trip.get("end_date") or "").strip()
    day_dates: list[str | None] = [None] * num_days
    if start_date_str:
        try:
            sd = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            day_dates = [(sd + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(num_days)]
            if not end_date_str:
                end_date_str = day_dates[-1]
        except ValueError:
            start_date_str = ""
            end_date_str = ""
    dates_label = f"{start_date_str} to {end_date_str}" if start_date_str and end_date_str else "Dates not set"

    stay = trip.get("stay") or trip.get("selected_stay") or {}
    hotel_name = stay.get("name") or f"{destination} Base Camp"
    s_lat = stay.get("lat") if stay.get("lat") is not None else stay.get("latitude")
    s_lon = stay.get("lon") if stay.get("lon") is not None else stay.get("longitude")
    hotel_coords = (
        (float(s_lat), float(s_lon))
        if s_lat is not None and s_lon is not None
        else None
    )
    early_checkin = bool(stay.get("early_checkin", False))

    transit = trip.get("transit") or {}
    transit_mode = (transit.get("mode") or trip.get("transport") or "car").lower()
    transit_title = transit.get("title") or transit.get("mode_title") or transit_mode.title()
    transit_available = transit.get("available", True) is not False
    if (not transit_available or "no direct flight" in transit_title.lower()) and transit_mode == "flight":
        transit_mode = "car"
        transit_available = False
    transit_dep_str = transit.get("departure") or "06:00"
    dep_mins = _parse_time_to_mins(transit_dep_str, 6 * 60)
    transit_dist_km = round(float(transit.get("distance_km") or 269.8), 1)
    raw_dur = transit.get("duration_mins") or transit.get("duration")
    if not raw_dur or str(raw_dur).strip() in ("—", "-", "N/A"):
        speed_kmh = {"car": 55.0, "bike": 45.0, "train": 55.0, "bus": 45.0, "flight": 620.0}.get(transit_mode, 50.0)
        transit_dur_mins = max(60, int(round((transit_dist_km / speed_kmh) * 60)))
        if transit_mode == "flight" and transit_available:
            transit_dur_mins += 90
    else:
        transit_dur_mins = _parse_duration_mins(raw_dur, 270)
    if transit_dist_km > 0 and transit_mode in ("train", "bus", "car", "bike"):
        max_spd = 75.0 if transit_mode in ("train", "car") else 65.0
        min_realistic_mins = int(round((transit_dist_km / max_spd) * 60))
        if transit_dur_mins < min_realistic_mins:
            transit_dur_mins = max(transit_dur_mins, int(round((transit_dist_km / 55.0) * 60)))
    arrival_mins = dep_mins + transit_dur_mins
    arrival_time_str = _fmt_time(arrival_mins)

    # Normalize selected sights
    raw_sights = trip.get("selected_attractions") or []
    sights = []
    _TREK_KEYWORDS = (
        "trek", "peak", "tadiandamol", "tadiyandmol", "kudremukh",
        "mullayanagiri", "triund", "kedarkantha", "kumara parvatha",
        "brahmagiri", "chembra", "kodachadri", "skandagiri"
    )
    _KNOWN_TREK_KM = {
        "kudremukh": 22.0,
        "kumara parvatha": 22.0,
        "kedarkantha": 20.0,
        "triund": 18.0,
        "tadiandamol": 16.0,
        "tadiyandmol": 16.0,
        "brahmagiri": 16.0,
        "kodachadri": 14.0,
        "mullayanagiri": 12.0,
        "chembra": 12.0,
    }
    for a in raw_sights:
        lat = float(a["lat"]) if a.get("lat") is not None else None
        lon = float(a["lon"]) if a.get("lon") is not None else None
        dur_m = _parse_duration_mins(a.get("dur") or a.get("duration_mins") or 120, 120)
        s_name = a.get("name", "Sight")
        s_low = s_name.lower().strip()
        if s_low in ("hanging bridge", "bridge", "viewpoint", "waterfall", "temple", "unknown"):
            continue
        if "nalknad" in s_low:
            dur_m = min(dur_m, 45)
        if any(tk in s_low for tk in _TREK_KEYWORDS):
            trek_km = float(a.get("trek_km") or a.get("round_trip_km") or 0)
            if not trek_km:
                for k, km_val in _KNOWN_TREK_KM.items():
                    if k in s_low:
                        trek_km = km_val
                        break
            if not trek_km:
                m_km = re.search(r"(\d+(?:\.\d+)?)\s*km", s_low)
                if m_km:
                    trek_km = float(m_km.group(1))
            if trek_km > 20.0:
                dur_m = max(dur_m, 450)  # > 20km round trip -> 7.5h
            elif trek_km > 15.0:
                dur_m = max(dur_m, 360)  # > 15km round trip -> 6h
            elif trek_km > 10.0:
                dur_m = max(dur_m, 300)  # > 10km round trip -> 5h
            else:
                dur_m = max(dur_m, 300)  # Default trek/peak minimum -> 5h
        s_fee = int(float(a.get("fee") or 0))
        sights.append({
            "id": a.get("id", ""),
            "name": s_name,
            "cat": a.get("cat") or a.get("category") or "Sightseeing",
            "icon": a.get("icon") or "📍",
            "lat": lat,
            "lon": lon,
            "coords": (lat, lon) if lat is not None and lon is not None else None,
            "dur_mins": dur_m,
            "fee": s_fee,
            "dist_from_hotel": float(a.get("dist") or 12.0),
            "opening": a.get("opening"),
            "closed_days": str(a.get("closed_days") or ("Friday" if any(k in s_low for k in ("taj mahal", "sarnath")) else "")).lower(),
            "close_mins": _parse_closing_mins(a.get("opening"), 18 * 60 + 30),
        })

    warnings: list[str] = []
    arr_day_offset = arrival_mins // (24 * 60)
    if transit_dur_mins >= 720:
        warnings.append(
            f"Long {transit_mode} journey (~{_fmt_duration(transit_dur_mins)} each way) — "
            f"arrives Day {arr_day_offset + 1} at {_fmt_time(arrival_mins % (24 * 60))}. Consider Flight or Train for shorter trips."
        )

    # Distribute sights across days when traveler is actually at destination
    # Keep long treks (>= 4h) off the final departure day when earlier days exist
    sight_days = [idx for idx in range(num_days) if idx >= arr_day_offset]
    if not sight_days:
        sight_days = [num_days - 1]
    non_dep_days = [idx for idx in sight_days if idx < num_days - 1] or sight_days
    per_day: list[list[dict]] = [[] for _ in range(num_days)]
    for i, s in enumerate(sights):
        if s["dur_mins"] >= 240:
            target_d = non_dep_days[i % len(non_dep_days)]
        else:
            target_d = sight_days[i % len(sight_days)]
        per_day[target_d].append(s)

    days_out: list[dict] = []
    total_ss_dist_km = 0.0
    total_ss_drive_mins = 0
    hotel_dist_sum_km = 0.0

    for d_idx in range(num_days):
        day_num = d_idx + 1
        # Order sunrise sights first and sunset sights last within each day
        day_sights = sorted(
            per_day[d_idx],
            key=lambda x: (0 if "sunrise" in x["name"].lower() else (2 if "sunset" in x["name"].lower() else 1))
        )
        events: list[dict] = []
        day_drive_km = 0.0
        day_drive_mins = 0

        if day_num > 1 and d_idx < arr_day_offset:
            events.append({
                "start_time": "00:00",
                "end_time": "23:59",
                "duration_mins": 1440,
                "duration_label": "24h",
                "distance_km": 0.0,
                "distance_label": "in transit",
                "mode": transit_mode,
                "type": "travel",
                "icon": "🚌" if transit_mode == "bus" else ("🚆" if transit_mode == "train" else "🚗"),
                "from_place": source,
                "to_place": destination,
                "title": f"In Transit: {source} ➔ {destination} ({transit_title})",
                "subtitle": f"En route — arrives Day {arr_day_offset + 1} at {_fmt_time(arrival_mins % (24 * 60))}",
            })
            days_out.append({
                "day": day_num,
                "date": day_dates[d_idx],
                "sights": [],
                "events": events,
                "day_distance_km": 0.0,
                "day_drive_mins": 0,
                "day_drive_label": "0m",
            })
            continue

        if day_num == 1:
            if arr_day_offset >= 1:
                day1_mins = max(60, (24 * 60) - dep_mins)
                day1_dist = round(transit_dist_km * (day1_mins / max(1, transit_dur_mins)), 1)
                events.append({
                    "start_time": _fmt_time(dep_mins),
                    "end_time": "23:59",
                    "duration_mins": day1_mins,
                    "duration_label": _fmt_duration(day1_mins),
                    "distance_km": day1_dist,
                    "distance_label": "home → hotel",
                    "mode": transit_mode,
                    "type": "travel",
                    "icon": "🚗" if transit_mode == "car" else ("🚆" if transit_mode == "train" else ("🚌" if transit_mode == "bus" else "✈️")),
                    "from_place": source,
                    "to_place": destination,
                    "title": f"{transit_title}: {source} ➔ {destination}",
                    "subtitle": f"{transit_dist_km} km · {_fmt_duration(transit_dur_mins)} total · Arrives Day {arr_day_offset + 1} at {_fmt_time(arrival_mins % (24 * 60))}",
                })
                days_out.append({
                    "day": day_num,
                    "date": day_dates[d_idx],
                    "sights": [],
                    "events": events,
                    "day_distance_km": 0.0,
                    "day_drive_mins": 0,
                    "day_drive_label": "0m",
                })
                continue

            # Outbound transit leg (arrives same day)
            events.append({
                "start_time": _fmt_time(dep_mins),
                "end_time": arrival_time_str,
                "duration_mins": transit_dur_mins,
                "duration_label": _fmt_duration(transit_dur_mins),
                "distance_km": transit_dist_km,
                "distance_label": "home → hotel",
                "mode": transit_mode,
                "type": "travel",
                "icon": "🚗" if transit_mode == "car" else ("🚆" if transit_mode == "train" else ("🚌" if transit_mode == "bus" else "✈️")),
                "from_place": source,
                "to_place": hotel_name,
                "title": f"{transit_title}: {source} ➔ {destination}",
                "subtitle": f"{transit_dist_km} km · {_fmt_duration(transit_dur_mins)} · Arrives {arrival_time_str}",
            })
            cursor = arrival_mins

            # Check-in rule: standard check-in 12:00 unless early_checkin
            if cursor < 12 * 60 and not early_checkin:
                events.append({
                    "start_time": _fmt_time(cursor),
                    "end_time": _fmt_time(cursor + 30),
                    "duration_mins": 30,
                    "duration_label": "30m",
                    "distance_km": 0.0,
                    "distance_label": "",
                    "mode": "hotel",
                    "type": "hotel",
                    "icon": "🧳",
                    "from_place": hotel_name,
                    "to_place": hotel_name,
                    "title": f"Arrive at {hotel_name} — Luggage Drop & Refresh",
                    "subtitle": "Standard hotel check-in opens at 12:00 · Drop bags & freshen up",
                })
                cursor += 30
            else:
                events.append({
                    "start_time": _fmt_time(cursor),
                    "end_time": _fmt_time(cursor + 30),
                    "duration_mins": 30,
                    "duration_label": "30m",
                    "distance_km": 0.0,
                    "distance_label": "",
                    "mode": "hotel",
                    "type": "hotel",
                    "icon": "🏨",
                    "from_place": hotel_name,
                    "to_place": hotel_name,
                    "title": f"Arrive & Check-in at {hotel_name}",
                    "subtitle": "Room check-in & freshen up",
                })
                cursor += 30
        elif arr_day_offset >= 1 and d_idx == arr_day_offset:
            arr_local = arrival_mins % (24 * 60)
            if arr_local < 12 * 60 and not early_checkin:
                events.append({
                    "start_time": _fmt_time(arr_local),
                    "end_time": _fmt_time(arr_local + 30),
                    "duration_mins": 30,
                    "duration_label": "30m",
                    "distance_km": 0.0,
                    "distance_label": "",
                    "mode": "hotel",
                    "type": "hotel",
                    "icon": "🧳",
                    "from_place": hotel_name,
                    "to_place": hotel_name,
                    "title": f"Arrive at {hotel_name} — Early Luggage Drop",
                    "subtitle": "Standard room check-in opens at 12:00 · Drop luggage & freshen up",
                })
                rest_end = max(arr_local + 30, 8 * 60)
                _fill_gap_if_needed(events, arr_local + 30, rest_end, hotel_name)
                cursor = rest_end
                events.append({
                    "start_time": _fmt_time(cursor),
                    "end_time": _fmt_time(cursor + 30),
                    "duration_mins": 30,
                    "duration_label": "30m",
                    "distance_km": 0.0,
                    "distance_label": "",
                    "mode": "food",
                    "type": "food",
                    "icon": "☕",
                    "from_place": hotel_name,
                    "to_place": hotel_name,
                    "title": "Cafe Breakfast (Pre-Check-in)",
                    "subtitle": f"Breakfast near {hotel_name} before 12:00 room check-in",
                })
                cursor += 30
            else:
                cursor = max(arr_local, 8 * 60)
                events.append({
                    "start_time": _fmt_time(cursor),
                    "end_time": _fmt_time(cursor + 30),
                    "duration_mins": 30,
                    "duration_label": "30m",
                    "distance_km": 0.0,
                    "distance_label": "",
                    "mode": "hotel",
                    "type": "hotel",
                    "icon": "🏨",
                    "from_place": hotel_name,
                    "to_place": hotel_name,
                    "title": f"Arrive & Check-in at {hotel_name}",
                    "subtitle": "Room check-in & freshen up",
                })
                cursor += 30
        else:
            cursor = 8 * 60
            events.append({
                "start_time": _fmt_time(cursor),
                "end_time": _fmt_time(cursor + 30),
                "duration_mins": 30,
                "duration_label": "30m",
                "distance_km": 0.0,
                "distance_label": "",
                "mode": "food",
                "type": "food",
                "icon": "🍳",
                "from_place": hotel_name,
                "to_place": hotel_name,
                "title": "Hotel Breakfast",
                "subtitle": f"Start Day {day_num} at {hotel_name}",
            })
            cursor += 30

        prev_place = hotel_name
        prev_coords = hotel_coords
        lunch_added = False
        visited_sights: list[dict] = []

        day_weekday = ""
        if day_dates[d_idx]:
            try:
                day_weekday = datetime.strptime(day_dates[d_idx], "%Y-%m-%d").strftime("%A").lower()
            except Exception:
                day_weekday = ""

        for s in day_sights:
            if day_weekday and s.get("closed_days") and day_weekday in s["closed_days"]:
                if d_idx + 1 < num_days:
                    per_day[d_idx + 1].append(s)
                    warnings.append(f"{s['name']} is closed on {day_weekday.title()} — moved to Day {d_idx + 2}.")
                else:
                    warnings.append(f"{s['name']} is closed on {day_weekday.title()} — skipped from Day {day_num}.")
                continue

            # Direct hotel distance for Stage 3 sum
            h_km, _ = _osrm_leg(hotel_coords, s["coords"], s["dist_from_hotel"])
            hotel_dist_sum_km += h_km

            leg_km, leg_mins = _osrm_leg(prev_coords, s["coords"], s["dist_from_hotel"])
            is_hill_dest = any(k in destination.lower() for k in ("coorg", "madikeri", "shimla", "manali", "munnar", "ooty", "darjeeling", "gangtok", "wayanad", "chikmagalur"))
            if is_hill_dest and leg_km > 0:
                leg_mins = max(leg_mins, int(round((leg_km / 32.0) * 60)))
            elif leg_km >= 3.0 and leg_km < 30.0:
                leg_mins = max(leg_mins, int(round((leg_km / 28.0) * 60)))
            elif leg_km >= 30.0 and leg_km < 120.0:
                leg_mins = max(leg_mins, int(round((leg_km / 45.0) * 60)))
            dist_lbl = "hotel → sight" if prev_place == hotel_name else "sight → sight"

            # Wait until sunset/evening window for sunset points or Ganga Aarti
            s_nm_low = s["name"].lower()
            if ("sunset" in s_nm_low or "ganga aarti" in s_nm_low) and (cursor + leg_mins) < (16 * 60 + 30):
                wait_to = (17 * 60 if "ganga aarti" in s_nm_low else 16 * 60 + 30) - leg_mins
                if wait_to > cursor:
                    _fill_gap_if_needed(events, cursor, wait_to, prev_place)
                    cursor = wait_to

            # Check if sight + return fits before closing/dark (18:30 max), 12h day limit, and 115 km/day ghat drive cap
            lunch_offset = 45 if (not lunch_added and cursor >= 12 * 60) else 0
            ret_km_est, ret_mins_est = _osrm_leg(s["coords"], hotel_coords, s["dist_from_hotel"])
            if is_hill_dest and ret_km_est > 0:
                ret_mins_est = max(ret_mins_est, int(round((ret_km_est / 32.0) * 60)))
            projected_end = cursor + lunch_offset + leg_mins + s["dur_mins"]
            max_cutoff = min(s["close_mins"], 18 * 60 + 30)
            exceeds_drive_cap = is_hill_dest and (day_drive_km + leg_km + ret_km_est) > 115.0 and len(visited_sights) >= 1
            if exceeds_drive_cap or projected_end > max_cutoff or (projected_end + ret_mins_est - (arrival_mins if day_num == 1 else 480)) > 12 * 60:
                # Try moving to a later day if available
                if d_idx + 1 < num_days:
                    per_day[d_idx + 1].append(s)
                    warnings.append(
                        f"{s['name']} needs {_fmt_duration(leg_mins)} travel + {_fmt_duration(s['dur_mins'])} visit "
                        f"(would end {_fmt_time(projected_end)}) — moved to Day {d_idx + 2}."
                    )
                    continue
                warnings.append(
                    f"{s['name']} needs {_fmt_duration(leg_mins)} travel + {_fmt_duration(s['dur_mins'])} visit "
                    f"and does not fit before {_fmt_time(max_cutoff)} on Day {day_num} — removed from schedule."
                )
                continue

            # Insert lunch if crossing midday before travel/visit (only after confirming sight fits today)
            if not lunch_added and cursor >= 12 * 60:
                events.append({
                    "start_time": _fmt_time(cursor),
                    "end_time": _fmt_time(cursor + 45),
                    "duration_mins": 45,
                    "duration_label": "45m",
                    "distance_km": 0.0,
                    "distance_label": "",
                    "mode": "food",
                    "type": "food",
                    "icon": "🍽️",
                    "from_place": prev_place,
                    "to_place": prev_place,
                    "title": "Lunch Break",
                    "subtitle": f"Local meal before heading to {s['name']}",
                })
                cursor += 45
                lunch_added = True

            # Travel leg to sight
            events.append({
                "start_time": _fmt_time(cursor),
                "end_time": _fmt_time(cursor + leg_mins),
                "duration_mins": leg_mins,
                "duration_label": _fmt_duration(leg_mins),
                "distance_km": leg_km,
                "distance_label": dist_lbl,
                "mode": "car",
                "type": "travel",
                "icon": "🚗",
                "from_place": prev_place,
                "to_place": s["name"],
                "title": f"Drive: {prev_place} ➔ {s['name']}",
                "subtitle": f"{leg_km} km ({dist_lbl}) · {_fmt_duration(leg_mins)}",
            })
            cursor += leg_mins
            day_drive_km += leg_km
            day_drive_mins += leg_mins

            # Sight visit
            events.append({
                "start_time": _fmt_time(cursor),
                "end_time": _fmt_time(cursor + s["dur_mins"]),
                "duration_mins": s["dur_mins"],
                "duration_label": _fmt_duration(s["dur_mins"]),
                "distance_km": 0.0,
                "distance_label": "",
                "mode": "sightseeing",
                "type": "attraction",
                "icon": s["icon"],
                "from_place": s["name"],
                "to_place": s["name"],
                "title": s["name"],
                "subtitle": f"{s['cat']} · {_fmt_duration(s['dur_mins'])} visit · {'₹' + str(s['fee']) if s['fee'] > 0 else 'Free'}",
                "attractionId": s["id"],
            })
            cursor += s["dur_mins"]
            prev_place = s["name"]
            prev_coords = s["coords"]
            visited_sights.append(s)

        # Return-to-hotel leg after last sight
        if prev_place != hotel_name:
            last_dist_fb = visited_sights[-1]["dist_from_hotel"] if visited_sights else 4.0
            ret_km, ret_mins = _osrm_leg(prev_coords, hotel_coords, last_dist_fb)
            is_hill_dest = any(k in destination.lower() for k in ("coorg", "madikeri", "shimla", "manali", "munnar", "ooty", "darjeeling", "gangtok", "wayanad", "chikmagalur"))
            if is_hill_dest and ret_km > 0:
                ret_mins = max(ret_mins, int(round((ret_km / 32.0) * 60)))
            elif ret_km >= 3.0 and ret_km < 30.0:
                ret_mins = max(ret_mins, int(round((ret_km / 28.0) * 60)))
            events.append({
                "start_time": _fmt_time(cursor),
                "end_time": _fmt_time(cursor + ret_mins),
                "duration_mins": ret_mins,
                "duration_label": _fmt_duration(ret_mins),
                "distance_km": ret_km,
                "distance_label": "sight → hotel",
                "mode": "car",
                "type": "travel",
                "icon": "🏨",
                "from_place": prev_place,
                "to_place": hotel_name,
                "title": f"Return to {hotel_name}",
                "subtitle": f"{ret_km} km (sight → hotel) · {_fmt_duration(ret_mins)}",
            })
            cursor += ret_mins
            day_drive_km += ret_km
            day_drive_mins += ret_mins

        day_base_mins = (cursor // (24 * 60)) * (24 * 60)
        dinner_start = max(cursor, day_base_mins + 19 * 60)
        _fill_gap_if_needed(events, cursor, dinner_start, hotel_name)
        cursor = dinner_start

        if day_num < num_days:
            events.append({
                "start_time": _fmt_time(cursor),
                "end_time": _fmt_time(cursor + 60),
                "duration_mins": 60,
                "duration_label": "1h",
                "distance_km": 0.0,
                "distance_label": "",
                "mode": "food",
                "type": "food",
                "icon": "🌙",
                "from_place": hotel_name,
                "to_place": hotel_name,
                "title": "Dinner & Overnight Stay",
                "subtitle": f"Dinner and rest at {hotel_name}",
            })
        else:
            # Final day: dinner, explicit check-out, and real return journey leg
            events.append({
                "start_time": _fmt_time(cursor),
                "end_time": _fmt_time(cursor + 45),
                "duration_mins": 45,
                "duration_label": "45m",
                "distance_km": 0.0,
                "distance_label": "",
                "mode": "food",
                "type": "food",
                "icon": "🍽️",
                "from_place": hotel_name,
                "to_place": hotel_name,
                "title": "Dinner before Departure",
                "subtitle": f"Farewell dinner near {hotel_name}",
            })
            cursor += 45

            events.append({
                "start_time": _fmt_time(cursor),
                "end_time": _fmt_time(cursor + 15),
                "duration_mins": 15,
                "duration_label": "15m",
                "distance_km": 0.0,
                "distance_label": "",
                "mode": "hotel",
                "type": "hotel",
                "icon": "🧳",
                "from_place": hotel_name,
                "to_place": hotel_name,
                "title": f"Hotel Check-out from {hotel_name}",
                "subtitle": "Settle room bill & load luggage",
            })
            cursor += 15

            is_active_flight = (transit_mode == "flight" and transit_available)
            buffer_mins = 90 if is_active_flight else 30
            ret_dep = max(cursor + buffer_mins, 20 * 60)
            _fill_gap_if_needed(events, cursor, ret_dep - buffer_mins, hotel_name)
            events.append({
                "start_time": _fmt_time(ret_dep - buffer_mins),
                "end_time": _fmt_time(ret_dep),
                "duration_mins": buffer_mins,
                "duration_label": _fmt_duration(buffer_mins),
                "distance_km": 0.0,
                "distance_label": "",
                "mode": transit_mode,
                "type": "travel",
                "icon": "🛂" if is_active_flight else "🎫",
                "from_place": hotel_name,
                "to_place": hotel_name,
                "title": f"{'Airport Check-in & Security Buffer' if is_active_flight else 'Departure Prep / Boarding Buffer'}",
                "subtitle": f"Arrive {_fmt_duration(buffer_mins)} before {transit_mode} departure",
            })
            ret_arr = ret_dep + transit_dur_mins
            next_day = ret_arr >= 24 * 60
            if next_day:
                warnings.append(
                    f"Return to {source} departs {_fmt_time(ret_dep)} and arrives {_fmt_time(ret_arr)} (after midnight)."
                )
            events.append({
                "start_time": _fmt_time(ret_dep),
                "end_time": _fmt_time(ret_arr),
                "duration_mins": transit_dur_mins,
                "duration_label": _fmt_duration(transit_dur_mins),
                "distance_km": transit_dist_km,
                "distance_label": "hotel → home",
                "mode": transit_mode,
                "type": "travel",
                "icon": "🏠",
                "from_place": hotel_name,
                "to_place": source,
                "title": f"Return to {source} ({transit_title})",
                "subtitle": (
                    f"{transit_dist_km} km (hotel → home) · {_fmt_duration(transit_dur_mins)} · "
                    f"Arrives {_fmt_time(ret_arr)}" + (" — arrives after midnight" if next_day else "")
                ),
                "next_day_arrival": next_day,
            })

        day_drive_km = round(day_drive_km, 1)
        total_ss_dist_km += day_drive_km
        total_ss_drive_mins += day_drive_mins

        days_out.append({
            "day": day_num,
            "date": day_dates[d_idx],
            "sights": visited_sights,
            "events": events,
            "day_distance_km": day_drive_km,
            "day_drive_mins": day_drive_mins,
            "day_drive_label": _fmt_duration(day_drive_mins),
        })

    scheduled_sights = [s for d in days_out for s in (d.get("sights") or [])]
    trip_for_totals = dict(trip)
    trip_for_totals["_arr_day_offset"] = arr_day_offset
    if scheduled_sights:
        trip_for_totals["selected_attractions"] = scheduled_sights
    totals = calculate_trip_total(trip_for_totals)
    if arr_day_offset >= 1:
        warnings.append(
            f"Outbound transit arrives Day {arr_day_offset + 1}: stay is billed only for {totals['nights']} occupied night(s) (no wasted hotel nights while in transit)."
        )
    if totals["budget_target"] > 0 and totals["transit_group"] >= 0.75 * totals["budget_target"]:
        pct_t = round((totals["transit_group"] / totals["budget_target"]) * 100)
        warnings.append(
            f"Transit alone (₹{totals['transit_group']:,}) uses {pct_t}% of your ₹{totals['budget_target']:,} budget — consider Train/Bus or increasing your budget."
        )

    result = {
        "source": source,
        "destination": destination,
        "dates_label": dates_label,
        "start_date": start_date_str or None,
        "end_date": end_date_str or None,
        "arrival_time": arrival_time_str,
        "transit": {
            "mode": transit_mode,
            "available": transit_available,
            "title": transit_title,
            "departure": _fmt_time(dep_mins),
            "arrival": arrival_time_str,
            "duration_mins": transit_dur_mins,
            "duration_label": _fmt_duration(transit_dur_mins),
            "distance_km": transit_dist_km,
            "fare_per_person": totals["transit_per_person"],
        },
        "days": days_out,
        "claimed_sight_count": sum(len(d.get("sights") or []) for d in days_out),
        "total_distance_km": round(total_ss_dist_km, 1),
        "total_drive_mins": total_ss_drive_mins,
        "total_drive_label": _fmt_duration(total_ss_drive_mins),
        "hotel_distances_sum_km": round(hotel_dist_sum_km, 1),
        "warnings": warnings,
        "budget": totals,
    }
    from backend.services.itinerary.feasibility_validator import repair_and_validate_timeline
    result["feasibility"] = repair_and_validate_timeline(result)
    return result
