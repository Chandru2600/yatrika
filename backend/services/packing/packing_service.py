"""
Yatrika - Destination-Aware Smart Packing Checklist Service
Generates context-aware, destination-tailored packing checklists based on
regional climate, trip duration, transit mode, and weather signals.
"""

from typing import Dict, Any, List


BEACH_DESTINATIONS = {
    "goa", "gokarna", "pondicherry", "puducherry", "kerala", "kovalam", "varkala",
    "andaman", "havelock", "neil", "mumbai", "alibaug", "daman", "diu", "puri",
    "visakhapatnam", "vizag", "chennai", "mahabalipuram", "mangalore", "lakshadweep"
}

HILL_DESTINATIONS = {
    "manali", "shimla", "ladakh", "leh", "srinagar", "gulmarg", "pahalgam",
    "ooty", "munnar", "kodaikanal", "darjeeling", "gangtok", "mussoorie",
    "nainital", "dharamshala", "mcleodganj", "kasol", "rishikesh", "coorg",
    "wayanad", "shillong", "tawang", "spiti", "kullu", "dalhousie"
}


def _infer_weather_signals(trip: dict, weather: dict) -> Dict[str, Any]:
    """Derive temperature, precipitation, and climate context signals."""
    dest = (trip.get("destination") or "").lower()
    current = weather.get("current") if isinstance(weather, dict) else {}
    if not isinstance(current, dict):
        current = {}

    temp = current.get("temperature")
    desc = (current.get("description") or "").lower()
    forecast = weather.get("forecast") if isinstance(weather, dict) else []
    if isinstance(forecast, list):
        for f in forecast:
            if isinstance(f, dict):
                f_desc = (f.get("description") or "").lower()
                if "rain" in f_desc or "drizzle" in f_desc or "storm" in f_desc:
                    desc += f" {f_desc}"

    # Is beach / coastal
    is_beach = any(b in dest for b in BEACH_DESTINATIONS)
    # Is hill station / mountain
    is_hill = any(h in dest for h in HILL_DESTINATIONS)

    is_rainy = "rain" in desc or "drizzle" in desc or "storm" in desc or "monsoon" in desc
    is_hot = (temp is not None and temp >= 28.0) or is_beach
    is_cold = (temp is not None and temp <= 18.0) or is_hill

    context_tags = []
    if is_rainy:
        context_tags.append("Rain-Ready")
    if is_cold:
        context_tags.append("Warm Layers")
    elif is_hot:
        context_tags.append("Sun & Breathable")
    if is_beach:
        context_tags.append("Beach & Coastal")
    elif is_hill:
        context_tags.append("Mountain & Hiking")

    context_label = " · ".join(context_tags) if context_tags else "Standard Travel Essentials"

    return {
        "is_beach": is_beach,
        "is_hill": is_hill,
        "is_rainy": is_rainy,
        "is_hot": is_hot,
        "is_cold": is_cold,
        "context_label": context_label,
        "temp": temp
    }


def generate_smart_packing_checklist(trip: dict, weather: dict = None, existing_checklist: dict = None) -> dict:
    """
    Generate a categorized, destination-tailored packing checklist.
    Preserves packed status for items if existing_checklist is provided.
    """
    if weather is None:
        weather = {}

    signals = _infer_weather_signals(trip, weather)
    num_days = int(trip.get("num_days", 3) or 3)

    # Categories configuration
    essentials_items = [
        "Government Photo ID / Passport & Visa (if applicable)",
        "Flight / Train / Bus Booking Confirmations & Boarding Passes",
        "Wallet, Credit / Debit Cards & Backup Cash in INR",
        "Mobile Phone, Primary Charger & Sim Card",
        "Emergency Contact Card & Travel Insurance Details"
    ]

    clothing_items = [
        "Comfortable daytime casual wear (breathable t-shirts / shirts)",
        "Comfortable walking shoes or lightweight sneakers",
        "Sleepwear & lounge clothing",
        "Everyday socks and undergarments"
    ]

    if num_days >= 4:
        clothing_items.append("Extra pairs of undergarments & socks (4-6 pairs)")
        clothing_items.append("Travel laundry bag for worn clothes")

    if signals["is_rainy"]:
        clothing_items.append("Compact wind-resistant travel umbrella")
        clothing_items.append("Lightweight waterproof raincoat or poncho")
        clothing_items.append("Quick-drying activewear")

    if signals["is_hot"]:
        clothing_items.append("Wide-brim sun hat or baseball cap")
        clothing_items.append("UV400 protective sunglasses")
        clothing_items.append("Lightweight linen or moisture-wicking shirts")

    if signals["is_beach"]:
        clothing_items.append("Swimwear / beachwear")
        clothing_items.append("Flip-flops or water-resistant sandals")

    if signals["is_cold"]:
        clothing_items.append("Thermal innerwear (top & bottom)")
        clothing_items.append("Warm fleece jacket, sweater or down coat")
        clothing_items.append("Woolen beanie, scarf & gloves")
        clothing_items.append("Thick woolen socks & sturdy walking boots")

    health_items = [
        "Personal prescription medications & basic daily vitamins",
        "Travel first-aid kit (bandages, antiseptic ointment, pain relief)",
        "Hand sanitizer (travel size) & antibacterial wet wipes",
        "Sunscreen lotion (SPF 50+ PA+++) & hydrating lip balm",
        "Mosquito & insect repellent cream / spray",
        "Motion sickness & digestive relief tablets"
    ]

    electronics_items = [
        "High-capacity portable power bank (10,000+ mAh)",
        "Multi-port USB fast-charging cables (Type-C / Lightning)",
        "Noise-cancelling earphones or travel headphones",
        "Camera / GoPro & extra memory cards (optional)"
    ]

    destination_gear_items = [
        "Reusable insulated stainless steel water bottle",
        "Compact 15-20L daypack for daytime sightseeing loops",
        "Ziploc waterproof bags for wet clothes and toiletries",
        "Small TSA-approved travel lock for luggage security"
    ]

    if signals["is_rainy"]:
        destination_gear_items.append("Waterproof phone pouch & backpack rain cover")

    raw_categories = {
        "essentials": ("Documents & Essentials", "📄", essentials_items),
        "clothing": ("Clothing & Footwear", "👔", clothing_items),
        "health_care": ("Health & Personal Care", "💊", health_items),
        "electronics": ("Electronics & Gadgets", "📱", electronics_items),
        "destination_gear": ("Daypack & Exploration Gear", "🎒", destination_gear_items)
    }

    # Extract previously packed items map if existing checklist exists
    previously_packed = set()
    if existing_checklist and isinstance(existing_checklist, dict):
        # Support top-level checked_items list (from API payload)
        if "checked_items" in existing_checklist and isinstance(existing_checklist["checked_items"], list):
            for it in existing_checklist["checked_items"]:
                if isinstance(it, str):
                    previously_packed.add(it.strip().lower())

        # Support structured categories (from saved SQLite JSON)
        saved_cats = existing_checklist.get("categories", {})
        if isinstance(saved_cats, dict):
            for cat_key, cat_data in saved_cats.items():
                items_list = cat_data.get("items", []) if isinstance(cat_data, dict) else (cat_data if isinstance(cat_data, list) else [])
                for it in items_list:
                    if isinstance(it, dict) and it.get("packed"):
                        previously_packed.add(it.get("text", "").strip().lower())
                    elif isinstance(it, str):
                        previously_packed.add(it.strip().lower())

    # Build final structured output
    categories_output = {}
    total_count = 0
    packed_count = 0

    for cat_key, (cat_title, cat_icon, items) in raw_categories.items():
        structured_items = []
        for idx, item_text in enumerate(items, start=1):
            is_packed = item_text.strip().lower() in previously_packed
            structured_items.append({
                "id": f"{cat_key}_{idx}",
                "text": item_text,
                "packed": is_packed
            })
            total_count += 1
            if is_packed:
                packed_count += 1

        categories_output[cat_key] = {
            "title": cat_title,
            "icon": cat_icon,
            "items": structured_items
        }

    return {
        "trip_id": trip.get("id"),
        "destination": trip.get("destination", "Destination"),
        "weather_context": signals["context_label"],
        "categories": categories_output,
        "packed_count": packed_count,
        "total_count": total_count,
        "progress_pct": round((packed_count / total_count * 100) if total_count > 0 else 0)
    }
