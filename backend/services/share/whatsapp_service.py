"""
Yatrika - WhatsApp Share Service (Feature 5)
Generates compact, beautifully formatted trip summaries with WhatsApp markdown (*bold*, line breaks)
and pre-filled wa.me links with intelligent truncation to stay strictly within mobile limits.
"""

from typing import Dict, Any, Optional
import urllib.parse
from backend.services.booking.booking_service import build_booking_links

MAX_WHATSAPP_MESSAGE_CHARS = 1450


def generate_whatsapp_summary(
    trip: Dict[str, Any],
    itinerary: Optional[Dict[str, Any]] = None,
    budget: Optional[Dict[str, Any]] = None,
    booking_links: Optional[Dict[str, Any]] = None
) -> str:
    """
    Generate compact WhatsApp markdown trip summary:
    *bold*, line breaks, day-wise highlights with timings, total budget, booking links.
    Intelligently truncates if nearing WhatsApp character limits.
    """
    if not isinstance(trip, dict):
        trip = {}

    dest = trip.get("destination", "India")
    dest_clean = dest.split(",")[0].strip()
    start_date = trip.get("start_date", "Upcoming")
    end_date = trip.get("end_date", "")
    dates_str = f"{start_date} → {end_date}" if end_date else start_date
    num_days = trip.get("num_days", 1)
    travelers = trip.get("num_travelers", 1)

    # Budget resolution
    total_budget = 0
    if isinstance(budget, dict):
        total_budget = budget.get("total_budget_inr") or budget.get("total_budget") or 0
    if not total_budget:
        total_budget = trip.get("budget", 0)

    try:
        budget_str = f"₹{float(total_budget):,.0f}" if total_budget else "Flexible"
    except Exception:
        budget_str = str(total_budget)

    # Resolve booking links
    if not booking_links:
        try:
            booking_links = build_booking_links(trip)
        except Exception:
            booking_links = {}

    # Header section
    lines = [
        f"🌟 *YATRIKA TRIP: {dest_clean.upper()}*",
        f"📅 *Dates:* {dates_str} ({num_days} Days)",
        f"👥 *Travelers:* {travelers}",
        f"💰 *Estimated Budget:* {budget_str}",
        "",
        "📋 *DAY-WISE HIGHLIGHTS:*"
    ]

    # Itinerary days parsing
    days_data = []
    if isinstance(itinerary, dict):
        days_data = itinerary.get("days", [])
    elif isinstance(trip.get("itinerary_json"), str):
        import json
        try:
            parsed = json.loads(trip["itinerary_json"])
            if isinstance(parsed, dict):
                days_data = parsed.get("days", [])
        except Exception:
            pass

    # Build day summaries
    day_entries = []
    for day in days_data:
        day_num = day.get("day_number") or day.get("day") or 1
        day_date = day.get("date", "")
        day_header = f"🗓️ *Day {day_num}* ({day_date}):" if day_date else f"🗓️ *Day {day_num}:*"

        slots = []
        for slot_key, icon in [("morning", "🌅"), ("afternoon", "☀️"), ("evening", "🌙")]:
            slot_info = day.get(slot_key)
            if isinstance(slot_info, dict):
                name = slot_info.get("attraction") or slot_info.get("title") or slot_info.get("activity")
                time_val = slot_info.get("time") or slot_info.get("timing") or ""
                if name:
                    time_prefix = f"[{time_val}] " if time_val else ""
                    slots.append(f"  {icon} {time_prefix}{name}")
            elif isinstance(slot_info, str) and slot_info:
                slots.append(f"  {icon} {slot_info}")

        if not slots and day.get("title"):
            slots.append(f"  • {day.get('title')}")

        day_entries.append((day_header, slots))

    # Add days while respecting length limit
    added_days_count = 0
    for header, slots in day_entries:
        candidate_lines = [header] + slots + [""]
        candidate_text = "\n".join(lines + candidate_lines)

        # Check if adding this detailed day exceeds safety threshold
        if len(candidate_text) > (MAX_WHATSAPP_MESSAGE_CHARS - 350):
            # Switch to compact one-liner for remaining days
            remaining = len(day_entries) - added_days_count
            if remaining > 0:
                compact_names = []
                for h, sl in day_entries[added_days_count:]:
                    # Extract just names without timings
                    for s in sl:
                        clean_name = s.split("]")[-1].replace("🌅", "").replace("☀️", "").replace("🌙", "").strip()
                        if clean_name and clean_name not in compact_names:
                            compact_names.append(clean_name)
                if compact_names:
                    lines.append(f"🗓️ *More Highlights:* {', '.join(compact_names[:5])}...")
            break

        lines.extend(candidate_lines)
        added_days_count += 1

    # Booking links section
    hotel_url = ""
    train_url = ""
    bus_url = ""

    if isinstance(booking_links, dict):
        hotels = booking_links.get("hotels", [])
        if hotels and isinstance(hotels[0], dict):
            hotel_url = hotels[0].get("url", "")
        trains = booking_links.get("trains", [])
        if trains and isinstance(trains[0], dict):
            train_url = trains[0].get("url", "")
        buses = booking_links.get("buses", [])
        if buses and isinstance(buses[0], dict):
            bus_url = buses[0].get("url", "")

    booking_section = ["🔗 *QUICK BOOKING:*"]
    if hotel_url:
        booking_section.append(f"🏨 Stays: {hotel_url}")
    if train_url:
        booking_section.append(f"🚆 Trains: {train_url}")
    if bus_url:
        booking_section.append(f"🚌 Buses: {bus_url}")

    if len(booking_section) > 1:
        lines.append("")
        lines.extend(booking_section)

    lines.append("")
    lines.append("✈️ _Crafted by Yatrika AI Travel Planner_")

    result = "\n".join(lines)
    # Final safety clamp
    if len(result) > MAX_WHATSAPP_MESSAGE_CHARS:
        result = result[:MAX_WHATSAPP_MESSAGE_CHARS - 40] + "...\n\n✈️ _Crafted by Yatrika_"

    return result


def get_whatsapp_share_url(
    trip: Dict[str, Any],
    itinerary: Optional[Dict[str, Any]] = None,
    budget: Optional[Dict[str, Any]] = None,
    booking_links: Optional[Dict[str, Any]] = None
) -> str:
    """
    Generates ready-to-open wa.me link with URL-encoded text.
    """
    summary = generate_whatsapp_summary(trip, itinerary, budget, booking_links)
    encoded = urllib.parse.quote(summary)
    return f"https://wa.me/?text={encoded}"
