"""
Yatrika - iCalendar (.ics) Export Service (RFC 5545 Compliant)
"""

import re
import hashlib
from datetime import datetime, date, timedelta


def _escape_ics_text(text: str) -> str:
    """
    Escape special characters for iCalendar text properties according to RFC 5545 §3.3.11:
    - Backslash (\) -> \\
    - Semicolon (;) -> \;
    - Comma (,) -> \,
    - Newlines -> \n
    """
    if not text:
        return ""
    # Normalize CRLF and CR to LF
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Escape backslash first
    text = text.replace("\\", "\\\\")
    # Escape semicolon and comma
    text = text.replace(";", r"\;")
    text = text.replace(",", r"\,")
    # Escape newlines
    text = text.replace("\n", r"\n")
    return text


def _fold_ics_line(line: str, max_bytes: int = 75) -> str:
    """
    Fold iCalendar lines according to RFC 5545 §3.1:
    Lines of text SHOULD NOT be longer than 75 octets, excluding the line
    break. Long content lines are split with CRLF followed by a single space.
    """
    encoded = line.encode("utf-8")
    if len(encoded) <= max_bytes:
        return line

    chunks = []
    current_chunk = bytearray()
    limit = max_bytes

    for byte in encoded:
        current_chunk.append(byte)
        if len(current_chunk) >= limit:
            chunks.append(current_chunk.decode("utf-8", errors="ignore"))
            current_chunk = bytearray()
            # Folded continuation lines have space prefix, leaving 74 bytes
            limit = max_bytes - 1

    if current_chunk:
        chunks.append(current_chunk.decode("utf-8", errors="ignore"))

    return "\r\n ".join(chunks)


def _parse_trip_date(date_str: str) -> date:
    """Parse date string YYYY-MM-DD safely."""
    if not date_str:
        return date.today()
    try:
        return datetime.strptime(date_str.strip(), "%Y-%m-%d").date()
    except Exception:
        return date.today()


def _parse_duration_hours(dur_str: str, default_hours: float = 2.0) -> float:
    """Extract numeric hours from duration string like '2h', '3.5 hrs', '90 mins'."""
    if not dur_str or not isinstance(dur_str, str):
        return default_hours
    match_h = re.search(r'([\d.]+)\s*h', dur_str, re.IGNORECASE)
    if match_h:
        try:
            return float(match_h.group(1))
        except ValueError:
            pass
    match_m = re.search(r'(\d+)\s*m', dur_str, re.IGNORECASE)
    if match_m:
        try:
            return float(match_m.group(1)) / 60.0
        except ValueError:
            pass
    return default_hours


def generate_trip_ics(trip: dict, itinerary: dict) -> str:
    """
    Generate an RFC 5545 compliant .ics string for a saved Yatrika trip.
    Uses floating local time (RFC 5545 §3.3.5) for scheduled activities to
    preserve intended destination time without premature UTC conversion.
    """
    trip_id = trip.get("id", 1)
    destination = trip.get("destination", "Destination")
    dest_clean = destination.split(",")[0].strip()
    start_date = _parse_trip_date(trip.get("start_date", ""))
    dtstamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Yatrika//Travel Planner Agent//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:Yatrika - {_escape_ics_text(dest_clean)} Expedition"
    ]

    days = itinerary.get("days", [])
    if not days and isinstance(itinerary.get("itinerary"), dict):
        days = itinerary["itinerary"].get("days", [])

    # Standard default slot hours (start_hour, default_duration_hours)
    slot_schedules = {
        "morning":   (9, 0, 3.0),   # 09:00 - 12:00
        "afternoon": (14, 0, 3.0),  # 14:00 - 17:00
        "evening":   (18, 30, 2.0)  # 18:30 - 20:30
    }

    event_count = 0

    for day_idx, day_obj in enumerate(days, start=1):
        if not isinstance(day_obj, dict):
            continue

        day_num = day_obj.get("day", day_idx)
        try:
            day_num_int = int(day_num)
        except (ValueError, TypeError):
            day_num_int = day_idx

        # Calculate calendar date for this itinerary day
        day_date = start_date + timedelta(days=(day_num_int - 1))
        date_str_iso = day_date.strftime("%Y%m%d")

        for slot_key in ["morning", "afternoon", "evening"]:
            activity_data = day_obj.get(slot_key)
            if not activity_data:
                continue

            # Support activity as string or dict
            if isinstance(activity_data, str):
                summary = activity_data
                desc = f"Day {day_num_int} {slot_key.capitalize()} Activity in {dest_clean}."
                location = dest_clean
                dur_hours = slot_schedules[slot_key][2]
            elif isinstance(activity_data, dict):
                summary = (
                    activity_data.get("activity") or
                    activity_data.get("name") or
                    activity_data.get("place") or
                    f"Day {day_num_int} {slot_key.capitalize()} Activity"
                )
                desc_parts = []
                if activity_data.get("description"):
                    desc_parts.append(activity_data["description"])
                elif activity_data.get("desc"):
                    desc_parts.append(activity_data["desc"])

                if activity_data.get("category"):
                    desc_parts.append(f"Category: {activity_data['category']}")
                if activity_data.get("cost") is not None:
                    desc_parts.append(f"Estimated Cost: INR {activity_data['cost']}")

                desc = " | ".join(desc_parts) if desc_parts else f"Yatrika curated activity for {dest_clean}."
                location = activity_data.get("location") or activity_data.get("place") or dest_clean
                dur_hours = _parse_duration_hours(activity_data.get("dur", ""), slot_schedules[slot_key][2])
            else:
                continue

            # Compute floating start and end times
            sh, sm, _ = slot_schedules[slot_key]
            start_dt = datetime(day_date.year, day_date.month, day_date.day, sh, sm, 0)
            end_dt = start_dt + timedelta(hours=dur_hours)

            dtstart_val = start_dt.strftime("%Y%m%dT%H%M%S")
            dtend_val = end_dt.strftime("%Y%m%dT%H%M%S")

            # Unique, stable UID for this specific activity
            uid_seed = f"yatrika-{trip_id}-d{day_num_int}-{slot_key}-{summary}"
            uid_hash = hashlib.sha1(uid_seed.encode("utf-8")).hexdigest()[:12]
            uid = f"yatrika-{trip_id}-d{day_num_int}-{slot_key}-{uid_hash}@yatrika.local"

            lines.append("BEGIN:VEVENT")
            lines.append(f"UID:{uid}")
            lines.append(f"DTSTAMP:{dtstamp}")
            lines.append(f"SUMMARY:{_escape_ics_text(summary)}")
            lines.append(f"DESCRIPTION:{_escape_ics_text(desc)}")
            lines.append(f"LOCATION:{_escape_ics_text(location)}")
            lines.append(f"DTSTART:{dtstart_val}")
            lines.append(f"DTEND:{dtend_val}")
            lines.append("STATUS:CONFIRMED")
            lines.append("END:VEVENT")

            event_count += 1

    # If itinerary had no timed activities, generate an all-day expedition banner event
    if event_count == 0:
        end_date = _parse_trip_date(trip.get("end_date", ""))
        # For all-day events, DTEND is exclusive so add 1 day
        exclusive_end = end_date + timedelta(days=1)
        uid = f"yatrika-trip-{trip_id}-allday@yatrika.local"

        lines.append("BEGIN:VEVENT")
        lines.append(f"UID:{uid}")
        lines.append(f"DTSTAMP:{dtstamp}")
        lines.append(f"SUMMARY:Yatrika Expedition: {_escape_ics_text(dest_clean)}")
        lines.append(f"DESCRIPTION:Exploration trip to {_escape_ics_text(destination)}.")
        lines.append(f"LOCATION:{_escape_ics_text(destination)}")
        lines.append(f"DTSTART;VALUE=DATE:{start_date.strftime('%Y%m%d')}")
        lines.append(f"DTEND;VALUE=DATE:{exclusive_end.strftime('%Y%m%d')}")
        lines.append("STATUS:CONFIRMED")
        lines.append("END:VEVENT")

    lines.append("END:VCALENDAR")

    # Apply RFC 5545 line folding and join with CRLF
    folded_lines = [_fold_ics_line(line) for line in lines]
    return "\r\n".join(folded_lines) + "\r\n"
