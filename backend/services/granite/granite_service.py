"""
TravelPlannerAgent - IBM Granite / watsonx.ai Service
Optimised: 2 API calls only per trip (fast generation).
"""

import re
import requests
import time
from backend.config import get_config

_token_cache: dict = {"token": None, "expires_at": 0}
IAM_TOKEN_URL = "https://iam.cloud.ibm.com/identity/token"


def get_ibm_iam_token() -> str:
    now = time.time()
    if _token_cache["token"] and now < _token_cache["expires_at"] - 60:
        return _token_cache["token"]
    cfg  = get_config()
    resp = requests.post(
        IAM_TOKEN_URL,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={"grant_type": "urn:ibm:params:oauth:grant-type:apikey", "apikey": cfg.IBM_API_KEY},
        timeout=30
    )
    resp.raise_for_status()
    td = resp.json()
    _token_cache["token"]      = td["access_token"]
    _token_cache["expires_at"] = now + td.get("expires_in", 3600)
    return _token_cache["token"]


def call_granite(prompt: str, max_tokens: int = 1200) -> str:
    """Single Granite API call."""
    cfg   = get_config()
    token = get_ibm_iam_token()
    resp  = requests.post(
        f"{cfg.IBM_WATSONX_URL}/ml/v1/text/generation?version=2023-05-29",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={
            "model_id":   cfg.GRANITE_MODEL_ID,
            "project_id": cfg.IBM_PROJECT_ID,
            "input":      prompt,
            "parameters": {"max_new_tokens": max_tokens, "min_new_tokens": 10,
                           "stop_sequences": ["<|endoftext|>"]}
        },
        timeout=120
    )
    resp.raise_for_status()
    return resp.json()["results"][0]["generated_text"].strip()


# ── Parser helpers ───────────────────────────────────────────────

def _extract(text: str, keyword: str, default: str = "") -> str:
    """Find a line starting with keyword (strips markdown noise) and return its value."""
    for line in text.split("\n"):
        clean = line.strip().lstrip("*-•# ").strip().lstrip("*").strip()
        if clean.lower().startswith(keyword.lower()):
            parts = clean.split(":", 1)
            return parts[1].strip() if len(parts) > 1 else default
    return default


def _extract_list(text: str, keyword: str) -> list:
    """Collect bullet lines after a keyword heading."""
    items, collecting = [], False
    for line in text.split("\n"):
        clean = line.strip().lstrip("*-•# ").strip().lstrip("*").strip()
        if clean.lower().startswith(keyword.lower()):
            collecting = True
            continue
        if collecting:
            if clean and any(clean.lower().startswith(k) for k in
                             ["clothes", "electronics", "medicines", "documents",
                              "accessories", "destination", "safety", "customs",
                              "budget", "hotel", "transport", "tip", "gem",
                              "morning", "afternoon", "evening", "theme"]):
                break
            item = clean.lstrip("0123456789.) ").strip()
            if len(item) > 2:
                items.append(item)
    return items[:6]


def _parse_pipe(raw: str, dest: str) -> dict:
    """Parse 'Place | Activity | Duration | Entry fee' pipe-separated line."""
    parts = [p.strip() for p in raw.split("|")]
    return {
        "place":     parts[0] if parts and parts[0] else dest,
        "activity":  parts[1] if len(parts) > 1 else "Sightseeing",
        "duration":  parts[2] if len(parts) > 2 else "2 hours",
        "entry_fee": parts[3] if len(parts) > 3 else "Free",
        "tips":      ""
    }


def _safe_num(text: str, default: float) -> float:
    nums = re.findall(r"\d+\.?\d*", str(text))
    return float(nums[0]) if nums else default


# ════════════════════════════════════════════════════════════════
#  CALL 1 — Full itinerary (overview + all days)
# ════════════════════════════════════════════════════════════════

def _call1_itinerary(dest, days, style, interests, reqs, start_date):
    """One Granite call for the complete itinerary."""
    from datetime import date, timedelta
    try:
        base = date.fromisoformat(start_date)
    except Exception:
        base = date.today()

    day_dates = [(base + timedelta(days=i)).isoformat() for i in range(days)]

    day_template = "\n".join([
        f"Day {i+1} ({day_dates[i]}):\n"
        f"Theme: [title]\n"
        f"Morning: [place] | [activity] | [duration] | [entry fee]\n"
        f"Afternoon: [place] | [activity] | [duration] | [entry fee]\n"
        f"Evening: [place] | [activity] | [duration] | [entry fee]\n"
        f"Lunch: [restaurant] | [cuisine] | [price]\n"
        f"Tip: [local tip]\n"
        f"Gem: [hidden gem]"
        for i in range(min(days, 5))
    ])

    prompt = (
        f"You are an expert travel guide for {dest}. "
        f"Create a complete {days}-day {style} itinerary. "
        f"Interests: {interests}. Requirements: {reqs or 'none'}.\n\n"
        f"First write:\n"
        f"Summary: [2 sentence trip overview]\n"
        f"Language: [local language]\n"
        f"Currency: [local currency]\n"
        f"Best time: [best month to visit]\n"
        f"Police: [emergency number]\n"
        f"Ambulance: [emergency number]\n"
        f"Packing clothes: [item1, item2, item3, item4]\n"
        f"Packing documents: [item1, item2, item3]\n"
        f"Packing medicines: [item1, item2]\n"
        f"Safety tip 1: [tip]\n"
        f"Safety tip 2: [tip]\n"
        f"Custom 1: [local custom]\n"
        f"Weather advice: [packing/clothing advice]\n\n"
        f"Then write each day exactly like this:\n\n"
        f"{day_template}"
    )

    return call_granite(prompt, max_tokens=1400), day_dates


def _parse_itinerary(text: str, dest: str, days: int, day_dates: list) -> dict:
    """Parse the itinerary call response into structured dict."""

    # ── Overview ─────────────────────────────────────────────
    overview = {
        "trip_summary":       _extract(text, "summary", f"A {days}-day trip to {dest}."),
        "best_time_to_visit": _extract(text, "best time", "Year-round"),
        "local_language":     _extract(text, "language", "Local"),
        "currency":           _extract(text, "currency", "Local currency"),
        "time_zone":          "Local timezone",
        "emergency_numbers": {
            "police":           _extract(text, "police",    "100"),
            "ambulance":        _extract(text, "ambulance", "108"),
            "tourist_helpline": "1363"
        }
    }

    # ── Packing ───────────────────────────────────────────────
    def csv_items(keyword):
        val = _extract(text, keyword, "")
        items = [i.strip().lstrip("*-• ") for i in val.split(",") if i.strip()]
        return items if items else []

    packing = {
        "clothes":                csv_items("packing clothes") or ["T-shirts", "Comfortable shoes", "Jacket"],
        "electronics":            ["Phone charger", "Power bank", "Camera"],
        "medicines":              csv_items("packing medicines") or ["Pain relief", "Antacid"],
        "documents":              csv_items("packing documents") or ["Passport", "ID card", "Tickets"],
        "accessories":            ["Sunglasses", "Backpack", "Umbrella"],
        "destination_essentials": ["Sunscreen", "Water bottle", "Local SIM"]
    }

    # ── Safety ────────────────────────────────────────────────
    safety = {
        "safety_tips":  [
            _extract(text, "safety tip 1", "Keep valuables secure"),
            _extract(text, "safety tip 2", "Carry a copy of your ID")
        ],
        "local_customs": [
            _extract(text, "custom 1", "Respect local traditions"),
        ],
        "useful_phrases": [
            {"phrase": "Hello",     "local": "Namaste",     "pronunciation": "nah-mas-tay"},
            {"phrase": "Thank you", "local": "Dhanyavaad",  "pronunciation": "dhan-ya-vaad"},
        ],
        "weather_advice": _extract(text, "weather advice", "Pack comfortable clothes."),
        "shopping_guide": {
            "markets":           [f"{dest} local bazaar"],
            "souvenirs":         [f"{dest} handicrafts", "Local sweets"],
            "price_negotiation": "Bargaining is common at local markets."
        }
    }

    # ── Day plans ─────────────────────────────────────────────
    day_plans = []
    for i in range(days):
        d_date = day_dates[i] if i < len(day_dates) else ""
        # Find section for this day in text
        day_marker = f"Day {i+1}"
        # Get the text block for this day
        day_start = text.lower().find(day_marker.lower())
        next_marker = text.lower().find(f"day {i+2}", day_start + 1) if i + 2 <= days else len(text)
        if day_start == -1:
            day_block = ""
        else:
            day_block = text[day_start: next_marker if next_marker != -1 else len(text)]

        def dextract(kw, dft=""):
            return _extract(day_block, kw, dft) if day_block else dft

        lunch_raw   = dextract("lunch")
        lunch_parts = [p.strip() for p in lunch_raw.split("|")]

        budget_val = _safe_num(dextract("budget", ""), 60)
        gem        = dextract("gem")
        theme      = dextract("theme", f"Exploring {dest} — Day {i+1}")

        day_plans.append({
            "day":       i + 1,
            "date":      d_date,
            "theme":     theme,
            "morning":   _parse_pipe(dextract("morning"),   dest),
            "afternoon": _parse_pipe(dextract("afternoon"), dest),
            "evening":   _parse_pipe(dextract("evening"),   dest),
            "food_recommendations": [{
                "meal":        "Lunch",
                "restaurant":  lunch_parts[0] if lunch_parts and lunch_parts[0] else "Local restaurant",
                "cuisine":     lunch_parts[1] if len(lunch_parts) > 1 else "Local",
                "price_range": lunch_parts[2] if len(lunch_parts) > 2 else "$$"
            }],
            "daily_budget": int(budget_val),
            "local_tips":   dextract("tip", f"Explore {dest} like a local."),
            "hidden_gems":  [gem] if gem else [f"Off-the-beaten path in {dest}"]
        })

    return {**overview, "days": day_plans, **packing, **safety}


# ════════════════════════════════════════════════════════════════
#  CALL 2 — Budget + Hotels + Transport
# ════════════════════════════════════════════════════════════════

def _call2_budget_hotels(dest, days, travelers, budget, style, transport):
    prompt = (
        f"Travel planning data for {dest}, {days} days, {travelers} people, "
        f"{budget} USD total, {style} style, {transport} transport.\n\n"
        f"Budget breakdown (give amounts adding to {budget}):\n"
        f"Accommodation: [USD amount]\n"
        f"Food: [USD amount]\n"
        f"Transportation: [USD amount]\n"
        f"Activities: [USD amount]\n"
        f"Shopping: [USD amount]\n"
        f"Emergency: [USD amount]\n"
        f"Misc: [USD amount]\n"
        f"Saving tip 1: [tip]\n"
        f"Saving tip 2: [tip]\n"
        f"Saving tip 3: [tip]\n\n"
        f"Hotel recommendations for {dest}:\n"
        f"Budget hotel 1: [name] | [price per night USD] | [rating/5] | [distance from center]\n"
        f"Budget hotel 2: [name] | [price per night USD] | [rating/5] | [distance from center]\n"
        f"Midrange hotel 1: [name] | [price per night USD] | [rating/5] | [distance from center]\n"
        f"Midrange hotel 2: [name] | [price per night USD] | [rating/5] | [distance from center]\n"
        f"Luxury hotel 1: [name] | [price per night USD] | [rating/5] | [distance from center]\n"
    )
    return call_granite(prompt, max_tokens=700)


def _parse_budget_hotels(text: str, dest: str, days: int,
                         travelers: int, total: float,
                         style: str, transport: str) -> tuple:

    # ── Budget ────────────────────────────────────────────────
    cats = {
        "accommodation": .30, "food": .20, "transportation": .18,
        "activities":    .12, "shopping": .10,
        "emergency":     .07, "misc": .03
    }
    cat_keys = {
        "accommodation": "accommodation", "food": "food",
        "transportation": "transportation", "activities": "activities_tickets",
        "shopping": "shopping", "emergency": "emergency_fund", "misc": "miscellaneous"
    }
    breakdown = {}
    for cat, pct in cats.items():
        raw_val = _extract(text, cat, "")
        amount  = _safe_num(raw_val, round(total * pct))
        key     = cat_keys[cat]
        breakdown[key] = {
            "amount":     amount,
            "percentage": round(amount / total * 100, 1),
            "details":    f"Estimated {cat} costs"
        }

    tips = [_extract(text, f"saving tip {i}", "") for i in range(1, 4)]
    tips = [t for t in tips if t] or [
        "Book accommodation 2 weeks in advance",
        "Use public transport instead of taxis",
        "Eat at local dhabas to save money"
    ]

    budget_data = {
        "total_budget":     total,
        "currency":         "USD",
        "breakdown":        breakdown,
        "daily_average":    round(total / days),
        "per_person_total": round(total / travelers),
        "budget_status":    "comfortable" if total > days * 60 else "tight",
        "saving_tips":      tips,
        "free_attractions": [f"Public parks and heritage walks in {dest}"],
        "best_value_tips":  [f"Visit {dest} during shoulder season for lower prices"]
    }

    # ── Hotels ────────────────────────────────────────────────
    def parse_hotel(line: str, fallback_name: str, fallback_price: int, fallback_rating: float):
        parts = [p.strip() for p in line.split("|")]
        name   = parts[0] if parts and len(parts[0]) > 1 else fallback_name
        price  = int(_safe_num(parts[1], fallback_price)) if len(parts) > 1 else fallback_price
        rating = _safe_num(parts[2], fallback_rating) if len(parts) > 2 else fallback_rating
        dist   = parts[3] if len(parts) > 3 else "2 km"
        return {
            "name":                 name[:50],
            "price_per_night":      price,
            "rating":               min(float(rating), 5.0),
            "distance_from_center": dist,
            "amenities":            ["WiFi", "AC", "Breakfast"],
            "pros":                 ["Good value", "Convenient"],
            "cons":                 ["Book in advance"],
            "booking_tip":          "Book 2 weeks early for best rates"
        }

    ppn = round(total * 0.30 / days)
    hotels_data = {
        "budget_hotels": [
            parse_hotel(_extract(text, "budget hotel 1"), f"Budget Inn {dest} 1", ppn//2,    3.5),
            parse_hotel(_extract(text, "budget hotel 2"), f"Budget Inn {dest} 2", ppn//2+10, 3.8),
        ],
        "mid_range_hotels": [
            parse_hotel(_extract(text, "midrange hotel 1"), f"Comfort Hotel {dest} 1", ppn,    4.2),
            parse_hotel(_extract(text, "midrange hotel 2"), f"Comfort Hotel {dest} 2", ppn+20, 4.4),
        ],
        "luxury_hotels": [
            parse_hotel(_extract(text, "luxury hotel 1"), f"Grand {dest} Hotel", ppn*2, 4.8),
        ],
        "recommended_area": f"City centre of {dest} — close to major attractions",
        "booking_advice":   "Book 2 weeks in advance for best availability and rates"
    }

    # ── Transport ─────────────────────────────────────────────
    transport_data = {
        "to_destination": [
            {
                "mode": transport.title(), "estimated_cost": round(total * 0.15),
                "duration": "Varies", "frequency": "Daily",
                "pros": ["Convenient", "Direct"], "cons": ["Book early"],
                "booking_tip": "Book 2-4 weeks ahead for best prices"
            },
            {
                "mode": "Bus", "estimated_cost": round(total * 0.05),
                "duration": "Varies", "frequency": "Multiple daily",
                "pros": ["Economical"], "cons": ["Slower"],
                "booking_tip": "Check state transport website"
            }
        ],
        "local_transport": [
            {"mode": "Auto Rickshaw / Taxi", "cost_range": "$2–10/trip",
             "availability": "6am–11pm", "recommended_for": "Sightseeing",
             "app_or_service": "Ola / Uber"},
            {"mode": "City Bus", "cost_range": "$0.20–1/trip",
             "availability": "5am–10pm", "recommended_for": "Budget travel",
             "app_or_service": "Google Maps"}
        ],
        "transport_passes": ["City bus day pass — unlimited travel"],
        "navigation_tips":  ["Download Google Maps offline before your trip",
                             "Pre-book airport/station transfers"],
        "scam_alerts":      ["Agree fare before boarding unlicensed autos",
                             "Use metered or app-based taxis"]
    }

    return budget_data, hotels_data, transport_data


# ════════════════════════════════════════════════════════════════
#  MAIN ORCHESTRATOR — 2 API calls total
# ════════════════════════════════════════════════════════════════

def generate_complete_travel_plan(trip_data: dict) -> dict:
    """
    Generate full travel plan with only 2 IBM Granite API calls.
    Fast, reliable, with graceful fallbacks.
    """
    dest       = trip_data.get("destination", "the destination")
    days       = int(trip_data.get("num_days", 3))
    travelers  = int(trip_data.get("num_travelers", 1))
    budget     = float(trip_data.get("budget", 1000))
    style      = trip_data.get("travel_style", "budget")
    transport  = trip_data.get("transport", "flight")
    interests  = ", ".join(trip_data.get("interests", ["sightseeing"])) or "sightseeing"
    reqs       = ", ".join(trip_data.get("special_requirements", [])) or ""
    start_date = trip_data.get("start_date", "2026-01-01")

    # ── Call 1: Itinerary ─────────────────────────────────────
    try:
        raw1, day_dates = _call1_itinerary(dest, days, style, interests, reqs, start_date)
        itinerary = _parse_itinerary(raw1, dest, days, day_dates)
    except Exception as e:
        from datetime import date, timedelta
        try:
            base = date.fromisoformat(start_date)
        except Exception:
            base = date.today()
        day_dates = [(base + timedelta(days=i)).isoformat() for i in range(days)]
        itinerary = {
            "trip_summary": f"A {days}-day {style} trip to {dest}.",
            "best_time_to_visit": "Year-round", "local_language": "Local",
            "currency": "Local currency", "time_zone": "Local",
            "emergency_numbers": {"police": "100", "ambulance": "108", "tourist_helpline": "1363"},
            "days": [{"day": i+1, "date": day_dates[i], "theme": f"Day {i+1} in {dest}",
                      "morning":   {"place": dest, "activity": "Morning sightseeing", "duration": "2 hours", "entry_fee": "Free", "tips": ""},
                      "afternoon": {"place": dest, "activity": "Cultural visit",       "duration": "3 hours", "entry_fee": "Varies", "tips": ""},
                      "evening":   {"place": dest, "activity": "Local market",         "duration": "2 hours", "entry_fee": "Free",   "tips": ""},
                      "food_recommendations": [{"meal": "Lunch", "restaurant": "Local restaurant", "cuisine": "Local", "price_range": "$$"}],
                      "daily_budget": round(budget / days), "local_tips": f"Explore {dest} at your own pace.",
                      "hidden_gems": [f"Off-the-beaten path in {dest}"]}
                     for i in range(days)],
            "clothes": ["T-shirts", "Comfortable shoes", "Jacket"],
            "electronics": ["Phone charger", "Power bank"],
            "medicines": ["Pain relief", "Antacid"],
            "documents": ["Passport", "ID card", "Tickets"],
            "accessories": ["Sunglasses", "Backpack"],
            "destination_essentials": ["Sunscreen", "Water bottle"],
            "safety_tips": ["Keep valuables secure", "Carry emergency contacts"],
            "local_customs": ["Respect local traditions"],
            "useful_phrases": [{"phrase": "Hello", "local": "Namaste", "pronunciation": "nah-mas-tay"}],
            "weather_advice": "Pack comfortable clothes.",
            "shopping_guide": {"markets": ["Local bazaar"], "souvenirs": ["Handicrafts"],
                               "price_negotiation": "Bargaining welcome at local markets."},
            "error": str(e)
        }

    # ── Call 2: Budget + Hotels + Transport ───────────────────
    try:
        raw2 = _call2_budget_hotels(dest, days, travelers, budget, style, transport)
        budget_data, hotels_data, transport_data = _parse_budget_hotels(
            raw2, dest, days, travelers, budget, style, transport)
    except Exception as e:
        pcts = {"accommodation": .30, "food": .20, "transportation": .18,
                "activities_tickets": .12, "shopping": .10, "emergency_fund": .07, "miscellaneous": .03}
        budget_data = {
            "total_budget": budget, "currency": "USD",
            "breakdown": {k: {"amount": round(budget*v), "percentage": round(v*100),
                              "details": k.replace("_", " ").title()} for k, v in pcts.items()},
            "daily_average": round(budget/days), "per_person_total": round(budget/travelers),
            "budget_status": "comfortable",
            "saving_tips": ["Book early", "Use public transport", "Eat local"],
            "free_attractions": ["Public parks"], "best_value_tips": ["Visit off-season"]
        }
        ppn = round(budget * 0.30 / days)
        def h(n, p, r): return {"name": n, "price_per_night": p, "rating": r, "distance_from_center": "2 km", "amenities": ["WiFi","AC"], "pros": ["Good value"], "cons": ["Basic"], "booking_tip": "Book in advance"}
        hotels_data = {
            "budget_hotels":    [h(f"Budget Inn {dest}", ppn//2, 3.5), h(f"Economy Stay {dest}", ppn//2+10, 3.8)],
            "mid_range_hotels": [h(f"Comfort Hotel {dest}", ppn, 4.2), h(f"City Hotel {dest}", ppn+20, 4.4)],
            "luxury_hotels":    [h(f"Grand {dest} Hotel", ppn*2, 4.8)],
            "recommended_area": f"City centre of {dest}",
            "booking_advice":   "Book 2 weeks ahead for best rates"
        }
        transport_data = {
            "to_destination": [{"mode": transport.title(), "estimated_cost": round(budget*.15), "duration": "Varies", "frequency": "Daily", "pros": ["Direct"], "cons": ["Book early"], "booking_tip": "Book 2 weeks early"}],
            "local_transport": [{"mode": "Taxi/Auto", "cost_range": "$2-10", "availability": "All day", "recommended_for": "Sightseeing", "app_or_service": "Ola/Uber"}],
            "transport_passes": ["City day pass"], "navigation_tips": ["Use Google Maps offline"],
            "scam_alerts": ["Agree fare before boarding"]
        }

    return {
        "itinerary": itinerary,
        "budget":    budget_data,
        "hotels":    hotels_data,
        "transport": transport_data,
        "error":     None
    }
