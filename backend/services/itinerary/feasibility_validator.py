"""
Yatrika Rule 0 & Rule 7: Standalone Deterministic Feasibility Validator.

Validates any generated timeline/plan BEFORE PDF export or summary rendering.
Returns per-check pass/fail results, errors, warnings, and a 0–10 feasibility score.
"""

from __future__ import annotations

from datetime import datetime
import re
from typing import Any

_HILL_DESTINATIONS = (
    "coorg", "madikeri", "shimla", "manali", "munnar", "ooty",
    "darjeeling", "gangtok", "wayanad", "chikmagalur", "kodaikanal",
    "nainital", "mussoorie",
)

_TREK_MIN_MINS = {
    "tadiandamol": 360,
    "tadiyandmol": 360,
    "kudremukh": 420,
    "kumara parvatha": 420,
    "kedarkantha": 360,
    "triund": 300,
    "brahmagiri": 300,
    "kodachadri": 300,
    "mullayanagiri": 240,
    "chembra": 300,
}

_BANNED_GENERIC_SIGHTS = {
    "hanging bridge", "bridge", "ridge point", "toy train", "vintage cars",
    "cliff jumping point", "temple elephant bathing", "rajiv gandhi 1944-91",
    "hamberg 40rp", "banaras locomotive works", "cave of nightmares",
    "a temple in my dream", "free view point",
}


def _parse_hhmm_mins(val: str | None) -> int | None:
    if not val:
        return None
    s = str(val).strip().upper()
    m = re.search(r"(\d{1,2}):(\d{2})", s)
    if not m:
        return None
    mins = int(m.group(1)) * 60 + int(m.group(2))
    day_m = re.search(r"\(\+(\d+)\s*DAY", s)
    if day_m:
        mins += int(day_m.group(1)) * 24 * 60
    return mins


def validate_trip_feasibility(plan_or_timeline: dict[str, Any]) -> dict[str, Any]:
    """
    Run all Rule 0 deterministic feasibility checks on a timeline or full plan dict.
    Returns {passed, score, checks, errors, warnings, summary}.
    """
    if "timeline" in plan_or_timeline and isinstance(plan_or_timeline["timeline"], dict):
        tl = plan_or_timeline["timeline"]
        outer_budget = plan_or_timeline.get("budget") or {}
    else:
        tl = plan_or_timeline
        outer_budget = {}

    destination = str(tl.get("destination") or plan_or_timeline.get("destination") or "").lower()
    is_hill = any(h in destination for h in _HILL_DESTINATIONS)
    days = tl.get("days") or []
    transit = tl.get("transit") or {}
    budget = tl.get("budget") or {}
    transit_mode = str(transit.get("mode") or plan_or_timeline.get("transport") or "car").lower()
    transit_avail = transit.get("available", True) is not False

    checks: list[dict[str, Any]] = []

    def _add_check(name: str, passed: bool, severity: str, message: str, details: dict | None = None) -> None:
        checks.append({
            "name": name,
            "passed": passed,
            "severity": severity,
            "message": message,
            "details": details or {},
        })

    # 1. Speed sanity check on every travel leg
    speed_failures = []
    for day_obj in days:
        day_num = day_obj.get("day", 1)
        for ev in day_obj.get("events") or []:
            if ev.get("type") != "travel":
                continue
            dist_km = float(ev.get("distance_km") or 0)
            dur_mins = int(ev.get("duration_mins") or 0)
            if dist_km <= 0 or dur_mins <= 0:
                continue
            implied_kmh = round(dist_km / (dur_mins / 60.0), 1)
            ev_mode = str(ev.get("mode") or transit_mode).lower()
            dist_lbl = str(ev.get("distance_label") or "").lower()
            is_intercity = ("home" in dist_lbl) or dist_km >= 120.0

            if ev_mode == "flight":
                max_kmh = 900.0
            elif ev_mode == "train":
                max_kmh = 80.0
            elif not is_intercity and is_hill:
                max_kmh = 40.0
            elif not is_intercity and dist_km >= 30.0:
                max_kmh = 50.0
            elif not is_intercity and dist_km >= 3.0:
                max_kmh = 30.0
            elif not is_intercity:
                max_kmh = 36.0
            else:
                max_kmh = 80.0

            if implied_kmh > max_kmh:
                speed_failures.append({
                    "day": day_num,
                    "title": ev.get("title"),
                    "distance_km": dist_km,
                    "duration_mins": dur_mins,
                    "implied_kmh": implied_kmh,
                    "max_kmh": max_kmh,
                })

    _add_check(
        "speed_sanity",
        len(speed_failures) == 0,
        "error",
        "All travel legs have realistic speeds." if not speed_failures else f"{len(speed_failures)} leg(s) exceed maximum realistic speed.",
        {"failures": speed_failures},
    )

    # 2. Budget reconciliation check
    budget_failures = []
    if budget:
        stay_g = float(budget.get("stay_group") or 0)
        transit_g = float(budget.get("transit_group") or 0)
        entry_g = float(budget.get("entry_group") or 0)
        food_g = float(budget.get("food_group") or 0)
        misc_g = float(budget.get("misc_group") or 0)
        group_tot = float(budget.get("group_total") or 0)
        calc_sum = stay_g + transit_g + entry_g + food_g + misc_g
        if abs(calc_sum - group_tot) > 2.0:
            budget_failures.append(f"Itemized sum ₹{calc_sum:,.0f} != group_total ₹{group_tot:,.0f}")
        if float(transit.get("distance_km") or 0) > 30 and transit_g <= 0:
            budget_failures.append("Inter-city transit fare is ₹0 for a >30 km trip.")
        if food_g <= 0 and len(days) > 0:
            budget_failures.append("Food allocation is ₹0.")
    if isinstance(outer_budget.get("breakdown"), dict) and outer_budget["breakdown"] and budget:
        bd_sum = sum(float(v.get("amount") or 0) for v in outer_budget["breakdown"].values() if isinstance(v, dict))
        if abs(bd_sum - float(budget.get("group_total") or 0)) > 2.0:
            budget_failures.append(f"Breakdown sum ₹{bd_sum:,.0f} != group_total ₹{float(budget.get('group_total') or 0):,.0f}")

    _add_check(
        "budget_reconciliation",
        len(budget_failures) == 0,
        "error",
        "Budget table reconciles cleanly." if not budget_failures else "; ".join(budget_failures),
        {"failures": budget_failures},
    )

    # 3. Sight count, duplicates, and generic labels
    scheduled_names: list[str] = []
    generic_hits: list[str] = []
    trek_short_hits: list[str] = []
    time_window_hits: list[str] = []
    closed_day_hits: list[str] = []
    overlap_hits: list[str] = []
    date_range_hits: list[str] = []

    dates_label = str(tl.get("dates_label") or "")
    start_bound = end_bound = None
    if " to " in dates_label:
        parts = dates_label.split(" to ")
        try:
            start_bound = datetime.strptime(parts[0].strip(), "%Y-%m-%d").date()
            end_bound = datetime.strptime(parts[1].strip(), "%Y-%m-%d").date()
        except Exception:
            start_bound = end_bound = None

    outbound_arr_mins = None
    if days:
        for ev in days[0].get("events") or []:
            if ev.get("type") == "travel" and ("home" in str(ev.get("distance_label") or "").lower() or float(ev.get("distance_km") or 0) >= 50):
                outbound_arr_mins = _parse_hhmm_mins(ev.get("end_time"))
                break

    for day_obj in days:
        day_num = day_obj.get("day", 1)
        d_str = day_obj.get("date")
        weekday = None
        if d_str:
            try:
                d_obj = datetime.strptime(str(d_str), "%Y-%m-%d").date()
                weekday = d_obj.strftime("%A").lower()
                if start_bound and end_bound and (d_obj < start_bound or d_obj > end_bound):
                    date_range_hits.append(f"Day {day_num} date {d_str} outside [{start_bound}, {end_bound}]")
            except Exception:
                pass

        prev_end = None
        for ev in day_obj.get("events") or []:
            st_m = _parse_hhmm_mins(ev.get("start_time"))
            en_m = _parse_hhmm_mins(ev.get("end_time"))
            if st_m is not None and en_m is not None:
                if prev_end is not None and st_m < prev_end - 1:
                    overlap_hits.append(f"Day {day_num}: '{ev.get('title')}' starts at {ev.get('start_time')} before previous ends")
                prev_end = en_m

            if ev.get("type") != "attraction":
                continue

            if day_num == 1 and outbound_arr_mins is not None and st_m is not None and st_m < outbound_arr_mins:
                overlap_hits.append(f"Day 1: '{ev.get('title')}' scheduled at {ev.get('start_time')} while in transit")

            title = str(ev.get("title") or "").strip()
            t_low = title.lower()
            scheduled_names.append(t_low)

            if t_low in _BANNED_GENERIC_SIGHTS:
                generic_hits.append(title)

            dur_m = int(ev.get("duration_mins") or 0)
            for trek_k, min_m in _TREK_MIN_MINS.items():
                if trek_k in t_low and dur_m < min_m:
                    trek_short_hits.append(f"{title} ({dur_m}m < {min_m}m required)")

            if weekday == "friday" and ("taj mahal" in t_low or "sarnath" in t_low):
                closed_day_hits.append(f"{title} scheduled on Friday (closed)")

            if st_m is not None:
                if "sunset" in t_low and st_m < 15 * 60 + 30:
                    time_window_hits.append(f"{title} scheduled at {ev.get('start_time')} (too early for sunset)")
                if "ganga aarti" in t_low and st_m < 17 * 60:
                    time_window_hits.append(f"{title} scheduled at {ev.get('start_time')} (before 17:00)")
                if "sarnath" in t_low and en_m is not None and en_m > 17 * 60 + 30:
                    time_window_hits.append(f"{title} ends at {ev.get('end_time')} (after 17:30 close)")

    dupes = sorted({n for n in scheduled_names if scheduled_names.count(n) > 1})
    claimed_count = tl.get("claimed_sight_count")
    count_mismatch = claimed_count is not None and int(claimed_count) != len(scheduled_names)

    _add_check(
        "sight_integrity",
        not dupes and not generic_hits and not count_mismatch,
        "error",
        "All sights are specific, unique, and match claimed count."
        if (not dupes and not generic_hits and not count_mismatch)
        else f"Sights issue: dupes={dupes}, generic={generic_hits}, count_mismatch={count_mismatch}",
        {"duplicates": dupes, "generic": generic_hits, "scheduled_count": len(scheduled_names), "claimed_count": claimed_count},
    )

    _add_check(
        "trek_durations",
        len(trek_short_hits) == 0,
        "error",
        "All treks meet minimum duration." if not trek_short_hits else "; ".join(trek_short_hits),
        {"short_treks": trek_short_hits},
    )

    _add_check(
        "dates_and_opening_windows",
        not date_range_hits and not closed_day_hits and not time_window_hits,
        "error",
        "All dates, closed days, and attraction time windows are valid."
        if (not date_range_hits and not closed_day_hits and not time_window_hits)
        else "; ".join(date_range_hits + closed_day_hits + time_window_hits),
        {"date_range": date_range_hits, "closed_days": closed_day_hits, "time_windows": time_window_hits},
    )

    _add_check(
        "no_overlaps",
        len(overlap_hits) == 0,
        "error",
        "Zero overlapping blocks or in-transit sightseeing." if not overlap_hits else "; ".join(overlap_hits),
        {"overlaps": overlap_hits},
    )

    # 4. Return leg & mode consistency
    return_failures = []
    if len(days) >= 2:
        last_events = days[-1].get("events") or []
        has_return = any(
            ev.get("type") == "travel" and ("return" in str(ev.get("title") or "").lower() or "home" in str(ev.get("distance_label") or "").lower())
            for ev in last_events
        )
        if not has_return:
            return_failures.append("Missing timed return leg on final day.")
        has_bad_airport_buf = any(
            "airport check-in" in str(ev.get("title") or "").lower() and (transit_mode != "flight" or not transit_avail)
            for ev in last_events
        )
        if has_bad_airport_buf:
            return_failures.append("Airport Check-in buffer scheduled for a non-flight journey.")

    _add_check(
        "return_leg",
        len(return_failures) == 0,
        "error",
        "Return leg and boarding buffer match transport mode." if not return_failures else "; ".join(return_failures),
        {"failures": return_failures},
    )

    errors = [c for c in checks if not c["passed"] and c["severity"] == "error"]
    warnings = [c for c in checks if not c["passed"] and c["severity"] == "warning"]
    score = round(max(0.0, 10.0 - (len(errors) * 1.5) - (len(warnings) * 0.5)), 1)
    passed = len(errors) == 0

    return {
        "passed": passed,
        "score": score,
        "checks": checks,
        "errors": errors,
        "warnings": warnings,
        "summary": f"Feasibility {score}/10 ({'PASS' if passed else f'FAIL: {len(errors)} error(s)'})",
    }


def _fmt_hhmm_offset(mins: int) -> str:
    m = max(0, int(round(mins)))
    day_off = m // (24 * 60)
    m_mod = m % (24 * 60)
    base = f"{m_mod // 60:02d}:{m_mod % 60:02d}"
    return f"{base} (+{day_off} day)" if day_off > 0 else base


def repair_and_validate_timeline(tl: dict[str, Any]) -> dict[str, Any]:
    """
    Self-correcting Critic & Auto-Repair Layer on top of Rule 0 validator.
    Detects feasibility errors, repairs them deterministically, re-validates,
    and records repair_actions + auto_repaired status.
    """
    initial = validate_trip_feasibility(tl)
    if initial["passed"]:
        initial["auto_repaired"] = False
        initial["repair_actions"] = []
        return initial

    actions: list[str] = []
    destination = str(tl.get("destination") or "").lower()
    is_hill = any(h in destination for h in _HILL_DESTINATIONS)
    transit = tl.get("transit") or {}
    transit_mode = str(transit.get("mode") or "car").lower()
    transit_avail = transit.get("available", True) is not False
    days = tl.get("days") or []

    seen_sights: set[str] = set()
    for day_obj in days:
        d_str = day_obj.get("date")
        weekday = None
        if d_str:
            try:
                weekday = datetime.strptime(str(d_str), "%Y-%m-%d").date().strftime("%A").lower()
            except Exception:
                weekday = None

        cleaned_events = []
        for ev in day_obj.get("events") or []:
            title = str(ev.get("title") or "").strip()
            t_low = title.lower()

            # 1. Strip invalid airport buffer on non-flight trips
            if "airport check-in" in t_low and (transit_mode != "flight" or not transit_avail):
                ev = dict(ev)
                ev["title"] = "Departure Prep / Boarding Buffer"
                ev["duration_mins"] = 30
                ev["duration_label"] = "30m"
                actions.append(f"Day {day_obj.get('day')}: replaced Airport Check-in with Departure Prep buffer")

            # 2. Remove generic/duplicate/closed-day attractions
            if ev.get("type") == "attraction":
                if t_low in _BANNED_GENERIC_SIGHTS:
                    actions.append(f"Day {day_obj.get('day')}: removed generic sight '{title}'")
                    continue
                if t_low in seen_sights:
                    actions.append(f"Day {day_obj.get('day')}: removed duplicate sight '{title}'")
                    continue
                if weekday == "friday" and ("taj mahal" in t_low or "sarnath" in t_low):
                    actions.append(f"Day {day_obj.get('day')}: removed Friday-closed '{title}'")
                    continue
                seen_sights.add(t_low)

                # 3. Enforce minimum trek duration
                for trek_k, min_m in _TREK_MIN_MINS.items():
                    if trek_k in t_low and int(ev.get("duration_mins") or 0) < min_m:
                        ev = dict(ev)
                        ev["duration_mins"] = min_m
                        ev["duration_label"] = f"{min_m // 60}h"
                        actions.append(f"Day {day_obj.get('day')}: expanded '{title}' to {min_m}m")
                        break

                # 4. Fix sunset / Ganga Aarti too early
                st_m = _parse_hhmm_mins(ev.get("start_time"))
                if st_m is not None and (("sunset" in t_low and st_m < 16 * 60) or ("ganga aarti" in t_low and st_m < 17 * 60)):
                    ev = dict(ev)
                    new_st = 17 * 60 if "ganga aarti" in t_low else 16 * 60 + 30
                    dur_m = int(ev.get("duration_mins") or 60)
                    ev["start_time"] = _fmt_hhmm_offset(new_st)
                    ev["end_time"] = _fmt_hhmm_offset(new_st + dur_m)
                    actions.append(f"Day {day_obj.get('day')}: shifted '{title}' to evening window")

            # 5. Repair impossible travel leg speeds
            if ev.get("type") == "travel":
                dist_km = float(ev.get("distance_km") or 0)
                dur_mins = int(ev.get("duration_mins") or 0)
                if dist_km > 0 and dur_mins > 0:
                    ev_mode = str(ev.get("mode") or transit_mode).lower()
                    dist_lbl = str(ev.get("distance_label") or "").lower()
                    is_intercity = ("home" in dist_lbl) or dist_km >= 120.0
                    max_kmh = 900.0 if ev_mode == "flight" else (80.0 if (ev_mode == "train" or is_intercity) else (40.0 if is_hill else (50.0 if dist_km >= 30.0 else 30.0)))
                    if (dist_km / (dur_mins / 60.0)) > max_kmh:
                        safe_spd = max_kmh * 0.85
                        new_mins = max(dur_mins, int(round((dist_km / safe_spd) * 60)))
                        ev = dict(ev)
                        ev["duration_mins"] = new_mins
                        ev["duration_label"] = f"{new_mins // 60}h {new_mins % 60}m" if new_mins >= 60 else f"{new_mins}m"
                        actions.append(f"Day {day_obj.get('day')}: adjusted '{title}' duration to {ev['duration_label']} for speed limit")

            cleaned_events.append(ev)

        # 6. Reflow event timestamps sequentially so there are zero overlaps
        prev_end = None
        for ev in cleaned_events:
            st_m = _parse_hhmm_mins(ev.get("start_time"))
            dur_m = int(ev.get("duration_mins") or 0)
            if st_m is not None and dur_m > 0:
                if prev_end is not None and st_m < prev_end:
                    st_m = prev_end
                    ev["start_time"] = _fmt_hhmm_offset(st_m)
                en_m = st_m + dur_m
                ev["end_time"] = _fmt_hhmm_offset(en_m)
                prev_end = en_m

        day_obj["events"] = cleaned_events
        day_obj["sights"] = [s for s in (day_obj.get("sights") or []) if str(s.get("name") or "").strip().lower() in seen_sights]

    if "claimed_sight_count" in tl:
        tl["claimed_sight_count"] = sum(
            1 for d in days for ev in (d.get("events") or []) if ev.get("type") == "attraction"
        )

    # 7. Reconcile budget totals
    budget = tl.get("budget")
    if isinstance(budget, dict) and budget:
        calc_sum = round(
            float(budget.get("stay_group") or 0)
            + float(budget.get("transit_group") or 0)
            + float(budget.get("entry_group") or 0)
            + float(budget.get("food_group") or 0)
            + float(budget.get("misc_group") or 0)
        )
        if abs(calc_sum - float(budget.get("group_total") or 0)) > 2.0:
            budget["group_total"] = calc_sum
            actions.append(f"Reconciled budget group_total to ₹{calc_sum:,}")

    rechecked = validate_trip_feasibility(tl)
    rechecked["auto_repaired"] = len(actions) > 0
    rechecked["repair_actions"] = actions
    return rechecked
