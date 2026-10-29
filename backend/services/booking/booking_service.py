"""
Yatrika - Actionable Booking Links Service (Feature 1)
Generates direct booking deep links for:
- Hotels: MakeMyTrip, Goibibo, Booking.com (prefilling destination, checkin/checkout, guests)
- Trains: IRCTC, ConfirmTkt (prefilling from-station, to-station, date)
- Buses: RedBus (prefilling from-city, to-city, date)

Requires zero external API keys. 100% URL construction with zero crash guarantee.
"""

from datetime import date, timedelta
from typing import Dict, Any, List
from urllib.parse import quote_plus


def _clean_city(city_str: str, default: str = "Bengaluru") -> str:
    """Extract clean city name from comma-separated location strings."""
    if not city_str:
        return default
    parts = str(city_str).split(",")
    first = parts[0].strip()
    return first if first else default


def _parse_dates(trip: Dict[str, Any]) -> tuple[date, date, int]:
    """Extract start_date, end_date, and num_days safely."""
    start_str = trip.get("start_date") or ""
    try:
        start_d = date.fromisoformat(str(start_str)[:10])
    except Exception:
        start_d = date.today() + timedelta(days=7)

    days = int(trip.get("num_days") or 3)
    if days < 1:
        days = 1

    end_str = trip.get("end_date") or ""
    try:
        end_d = date.fromisoformat(str(end_str)[:10])
    except Exception:
        end_d = start_d + timedelta(days=days)

    if end_d <= start_d:
        end_d = start_d + timedelta(days=max(1, days - 1))

    return start_d, end_d, days


def build_booking_links(trip: Dict[str, Any]) -> Dict[str, List[Dict[str, str]]]:
    """
    Build structured deep booking links for hotels, trains, and buses.
    Safe against empty or malformed trip data; guaranteed not to raise exceptions.
    """
    if not isinstance(trip, dict):
        trip = {}

    try:
        dest_city = _clean_city(trip.get("destination", "Coorg"), default="Coorg")
        src_city = _clean_city(trip.get("source", "Bengaluru"), default="Bengaluru")
        guests = int(trip.get("num_travelers") or 2)
        if guests < 1:
            guests = 1

        start_d, end_d, days = _parse_dates(trip)

        # Date string formats
        checkin_iso = start_d.isoformat()
        checkout_iso = end_d.isoformat()

        checkin_mmddyyyy = start_d.strftime("%m%d%Y")
        checkout_mmddyyyy = end_d.strftime("%m%d%Y")

        date_ddmmyyyy = start_d.strftime("%d%m%Y")
        date_dd_mm_yyyy = start_d.strftime("%d-%m-%Y")
        date_dd_mon_yyyy = start_d.strftime("%d-%b-%Y")

        # ── 1. Hotels Deep Links ─────────────────────────────────────
        # Booking.com
        booking_url = (
            f"https://www.booking.com/searchresults.html"
            f"?ss={quote_plus(dest_city)}"
            f"&checkin={checkin_iso}&checkout={checkout_iso}"
            f"&group_adults={guests}&no_rooms=1"
        )

        # MakeMyTrip
        mmt_url = (
            f"https://www.makemytrip.com/hotels/hotel-listing/?"
            f"city={quote_plus(dest_city)}"
            f"&checkin={checkin_mmddyyyy}&checkout={checkout_mmddyyyy}"
            f"&roomStayConfig=1e{guests}e0e"
        )

        # Goibibo
        goibibo_url = (
            f"https://www.goibibo.com/hotels/find-hotels-in-{quote_plus(dest_city.lower())}/?"
            f"checkin={checkin_iso}&checkout={checkout_iso}&guests={guests}"
        )

        hotel_links = [
            {
                "provider": "MakeMyTrip",
                "name": "MakeMyTrip",
                "url": mmt_url,
                "label": f"Book Hotels in {dest_city} on MakeMyTrip",
                "badge": "Popular in India",
                "icon": "bi-building"
            },
            {
                "provider": "Goibibo",
                "name": "Goibibo",
                "url": goibibo_url,
                "label": f"Search Hotels on Goibibo",
                "badge": "Best Rate Guarantee",
                "icon": "bi-tag-fill"
            },
            {
                "provider": "Booking.com",
                "name": "Booking.com",
                "url": booking_url,
                "label": f"Book on Booking.com",
                "badge": "Free Cancellation",
                "icon": "bi-globe2"
            }
        ]

        # ── 2. Train Deep Links ──────────────────────────────────────
        # ConfirmTkt
        confirmtkt_url = (
            f"https://www.confirmtkt.com/rbooking-d/trains/from/{quote_plus(src_city)}/to/{quote_plus(dest_city)}/{date_dd_mm_yyyy}"
        )

        # IRCTC
        irctc_url = (
            f"https://www.irctc.co.in/nget/train-search?"
            f"srcStation={quote_plus(src_city)}&destStation={quote_plus(dest_city)}&journeyDate={date_ddmmyyyy}"
        )

        train_links = [
            {
                "provider": "ConfirmTkt",
                "name": "ConfirmTkt",
                "url": confirmtkt_url,
                "label": f"Search Trains ({src_city} → {dest_city})",
                "badge": "Live Seat Probability",
                "icon": "bi-ticket-detailed-fill"
            },
            {
                "provider": "IRCTC",
                "name": "IRCTC Official",
                "url": irctc_url,
                "label": f"Book on IRCTC Official Portal",
                "badge": "Govt Ticket Booking",
                "icon": "bi-train-front-fill"
            }
        ]

        # ── 3. Bus Deep Links ───────────────────────────────────────
        # RedBus
        redbus_url = (
            f"https://www.redbus.in/bus-tickets/{quote_plus(src_city.lower())}-to-{quote_plus(dest_city.lower())}?"
            f"date={quote_plus(date_dd_mon_yyyy)}"
        )

        bus_links = [
            {
                "provider": "RedBus",
                "name": "RedBus",
                "url": redbus_url,
                "label": f"Book Buses on RedBus ({src_city} → {dest_city})",
                "badge": "State RTC & Private Sleeper",
                "icon": "bi-bus-front-fill"
            }
        ]

        return {
            "hotels": hotel_links,
            "trains": train_links,
            "buses": bus_links,
            "summary": {
                "destination": dest_city,
                "source": src_city,
                "checkin": checkin_iso,
                "checkout": checkout_iso,
                "guests": guests
            }
        }

    except Exception as e:
        # Zero crash fallback: return generic portals
        return {
            "hotels": [
                {
                    "provider": "MakeMyTrip",
                    "name": "MakeMyTrip",
                    "url": "https://www.makemytrip.com/hotels/",
                    "label": "Search Hotels on MakeMyTrip",
                    "badge": "Popular in India",
                    "icon": "bi-building"
                }
            ],
            "trains": [
                {
                    "provider": "ConfirmTkt",
                    "name": "ConfirmTkt",
                    "url": "https://www.confirmtkt.com/",
                    "label": "Search Trains on ConfirmTkt",
                    "badge": "Live Seat Probability",
                    "icon": "bi-train-front-fill"
                }
            ],
            "buses": [
                {
                    "provider": "RedBus",
                    "name": "RedBus",
                    "url": "https://www.redbus.in/",
                    "label": "Search Buses on RedBus",
                    "badge": "State RTC & Private",
                    "icon": "bi-bus-front-fill"
                }
            ],
            "summary": {"destination": "India", "source": "Bengaluru", "checkin": "", "checkout": "", "guests": 2}
        }
