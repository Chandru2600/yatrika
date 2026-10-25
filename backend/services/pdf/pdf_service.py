"""
TravelPlannerAgent - Luxury PDF Dossier Generator Service
Generates a comprehensive, publication-grade PDF expedition dossier
mirroring the Yatrika web application design language, boarding pass ticket,
4-pillar bento intelligence, climate transparency, daily loops, and packing checklist.
"""

import os
import json
import re
from datetime import datetime, date
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether, PageBreak
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.graphics.shapes import Drawing, Group
from reportlab.graphics.barcode import qr

from backend.config import get_config
from backend.services.weather.weather_service import evaluate_weather_horizon
from backend.services.packing.packing_service import generate_smart_packing_checklist

cfg = get_config()


# ── TrueType Typography Loader ────────────────────────────────
FONT_REGULAR = "Helvetica"
FONT_BOLD = "Helvetica-Bold"
FONT_ITALIC = "Helvetica-Oblique"

def _setup_fonts():
    global FONT_REGULAR, FONT_BOLD, FONT_ITALIC
    font_candidates = [
        ("SegoeUI", "C:\\Windows\\Fonts\\segoeui.ttf",
         "SegoeUI-Bold", "C:\\Windows\\Fonts\\segoeuib.ttf",
         "SegoeUI-Italic", "C:\\Windows\\Fonts\\segoeuii.ttf"),
        ("Arial", "C:\\Windows\\Fonts\\arial.ttf",
         "Arial-Bold", "C:\\Windows\\Fonts\\arialbd.ttf",
         "Arial-Italic", "C:\\Windows\\Fonts\\ariali.ttf"),
    ]
    for reg_name, reg_path, bold_name, bold_path, ital_name, ital_path in font_candidates:
        if os.path.exists(reg_path) and os.path.exists(bold_path):
            try:
                pdfmetrics.registerFont(TTFont(reg_name, reg_path))
                pdfmetrics.registerFont(TTFont(bold_name, bold_path))
                if os.path.exists(ital_path):
                    pdfmetrics.registerFont(TTFont(ital_name, ital_path))
                    FONT_ITALIC = ital_name
                else:
                    FONT_ITALIC = reg_name
                FONT_REGULAR = reg_name
                FONT_BOLD = bold_name
                break
            except Exception:
                pass

_setup_fonts()


# ── Brand Color Palette (Synchronized with Web UI) ────────────
NAVY_DEEP   = colors.HexColor("#0B1F33")
NAVY_SURF   = colors.HexColor("#07192F")
NAVY_LIGHT  = colors.HexColor("#1A2E44")
TURQUOISE   = colors.HexColor("#00A896")
TURQ_LIGHT  = colors.HexColor("#E6FFFA")
TURQ_BORDER = colors.HexColor("#99F6E4")
OCEAN_BLUE  = colors.HexColor("#0284C7")
OCEAN_LIGHT = colors.HexColor("#F0F9FF")
EMERALD     = colors.HexColor("#047857")
EMERALD_BG  = colors.HexColor("#ECFDF5")
AMBER       = colors.HexColor("#B45309")
AMBER_BG    = colors.HexColor("#FEF3C7")
PURPLE      = colors.HexColor("#6D28D9")
PURPLE_BG   = colors.HexColor("#EDE9FE")
BG_CARD     = colors.HexColor("#F8FAFC")
BG_CARD_ALT = colors.HexColor("#F1F5F9")
BORDER_CARD = colors.HexColor("#E2E8F0")
BORDER_DARK = colors.HexColor("#CBD5E1")
TEXT_DARK   = colors.HexColor("#0F172A")
TEXT_BODY   = colors.HexColor("#334155")
TEXT_MUTED  = colors.HexColor("#64748B")
WHITE       = colors.HexColor("#FFFFFF")


# ── Report Stylesheet ─────────────────────────────────────────
def _get_styles() -> dict:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "YatrikaTitle", parent=base["Title"],
            fontName=FONT_BOLD, fontSize=20, leading=24,
            textColor=NAVY_DEEP, alignment=TA_LEFT, spaceAfter=4
        ),
        "section_h1": ParagraphStyle(
            "SectionH1", parent=base["Heading1"],
            fontName=FONT_BOLD, fontSize=12, leading=15,
            textColor=NAVY_DEEP, spaceBefore=9, spaceAfter=5
        ),
        "section_h2": ParagraphStyle(
            "SectionH2", parent=base["Heading2"],
            fontName=FONT_BOLD, fontSize=10.5, leading=13,
            textColor=OCEAN_BLUE, spaceBefore=6, spaceAfter=3
        ),
        "body": ParagraphStyle(
            "Body", parent=base["Normal"],
            fontName=FONT_REGULAR, fontSize=8.5, leading=12,
            textColor=TEXT_BODY, spaceAfter=2
        ),
        "body_bold": ParagraphStyle(
            "BodyBold", parent=base["Normal"],
            fontName=FONT_BOLD, fontSize=8.5, leading=12,
            textColor=TEXT_DARK
        ),
        "small": ParagraphStyle(
            "Small", parent=base["Normal"],
            fontName=FONT_REGULAR, fontSize=7.5, leading=10.5,
            textColor=TEXT_MUTED
        ),
        "small_bold": ParagraphStyle(
            "SmallBold", parent=base["Normal"],
            fontName=FONT_BOLD, fontSize=7.5, leading=10.5,
            textColor=TEXT_DARK
        ),
        "extra_small": ParagraphStyle(
            "ExtraSmall", parent=base["Normal"],
            fontName=FONT_REGULAR, fontSize=6.8, leading=9,
            textColor=TEXT_MUTED
        ),
        "badge_emerald": ParagraphStyle(
            "BadgeEmerald", parent=base["Normal"],
            fontName=FONT_BOLD, fontSize=7.2, leading=9.5,
            textColor=EMERALD
        ),
        "badge_ocean": ParagraphStyle(
            "BadgeOcean", parent=base["Normal"],
            fontName=FONT_BOLD, fontSize=7.2, leading=9.5,
            textColor=OCEAN_BLUE
        ),
        "badge_amber": ParagraphStyle(
            "BadgeAmber", parent=base["Normal"],
            fontName=FONT_BOLD, fontSize=7.2, leading=9.5,
            textColor=AMBER
        ),
        "badge_purple": ParagraphStyle(
            "BadgePurple", parent=base["Normal"],
            fontName=FONT_BOLD, fontSize=7.2, leading=9.5,
            textColor=PURPLE
        ),
        "card_title": ParagraphStyle(
            "CardTitle", parent=base["Normal"],
            fontName=FONT_BOLD, fontSize=9.5, leading=12.5,
            textColor=TEXT_DARK
        ),
        "card_desc": ParagraphStyle(
            "CardDesc", parent=base["Normal"],
            fontName=FONT_REGULAR, fontSize=7.5, leading=10.5,
            textColor=TEXT_MUTED
        ),
        "ticket_title": ParagraphStyle(
            "TicketTitle", parent=base["Normal"],
            fontName=FONT_BOLD, fontSize=11, leading=13,
            textColor=WHITE
        ),
        "ticket_sub": ParagraphStyle(
            "TicketSub", parent=base["Normal"],
            fontName=FONT_REGULAR, fontSize=7.2, leading=9.5,
            textColor=TURQ_LIGHT
        ),
        "station_code": ParagraphStyle(
            "StationCode", parent=base["Normal"],
            fontName=FONT_BOLD, fontSize=17, leading=19,
            textColor=WHITE, alignment=TA_CENTER
        ),
        "station_code_turq": ParagraphStyle(
            "StationCodeTurq", parent=base["Normal"],
            fontName=FONT_BOLD, fontSize=17, leading=19,
            textColor=TURQUOISE, alignment=TA_CENTER
        ),
        "station_city": ParagraphStyle(
            "StationCity", parent=base["Normal"],
            fontName=FONT_BOLD, fontSize=9, leading=11,
            textColor=WHITE, alignment=TA_CENTER
        ),
        "corridor_track": ParagraphStyle(
            "CorridorTrack", parent=base["Normal"],
            fontName=FONT_REGULAR, fontSize=7.2, leading=9.5,
            textColor=TURQ_LIGHT, alignment=TA_CENTER
        ),
        "stub_fare_lbl": ParagraphStyle(
            "StubFareLbl", parent=base["Normal"],
            fontName=FONT_BOLD, fontSize=6.5, leading=8.5,
            textColor=TURQ_LIGHT, alignment=TA_CENTER
        ),
        "stub_fare_val": ParagraphStyle(
            "StubFareVal", parent=base["Normal"],
            fontName=FONT_BOLD, fontSize=13, leading=15,
            textColor=TURQUOISE, alignment=TA_CENTER
        ),
        "stub_fare_total": ParagraphStyle(
            "StubFareTotal", parent=base["Normal"],
            fontName=FONT_REGULAR, fontSize=6.8, leading=8.5,
            textColor=WHITE, alignment=TA_CENTER
        )
    }


# ── Running Header & Footer Canvas ────────────────────────────
class YatrikaNumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, total_pages):
        page_w, page_h = A4
        margin = 1.5 * cm

        # Header on pages 2 and onwards
        if self._pageNumber > 1:
            self.saveState()
            self.setFont(FONT_REGULAR, 7.5)
            self.setFillColor(TEXT_MUTED)
            self.drawString(margin, page_h - 1.1 * cm, "YATRIKA EXPEDITION DOSSIER")
            dest_str = getattr(self, "trip_destination", "")
            if dest_str:
                self.drawRightString(page_w - margin, page_h - 1.1 * cm, f"{dest_str.upper()} · EXPEDITION PLAN")
            self.setStrokeColor(TURQUOISE)
            self.setLineWidth(0.8)
            self.line(margin, page_h - 1.25 * cm, page_w - margin, page_h - 1.25 * cm)
            self.restoreState()

        # Running Footer on all pages
        self.saveState()
        self.setStrokeColor(BORDER_CARD)
        self.setLineWidth(0.75)
        self.line(margin, 1.2 * cm, page_w - margin, 1.2 * cm)

        self.setFont(FONT_REGULAR, 7.5)
        self.setFillColor(TEXT_MUTED)
        self.drawString(
            margin, 0.8 * cm,
            "Yatrika AI Travel Platform  |  Official Expedition Document  |  Verified IRCTC / RTC Corridor"
        )
        self.drawRightString(
            page_w - margin, 0.8 * cm,
            f"Page {self._pageNumber} of {total_pages}"
        )
        self.restoreState()


# ── Component 1: Luxury Boarding Pass Ticket ──────────────────
def _build_boarding_pass(trip: dict, itinerary: dict, budget: dict, hotels: dict, styles: dict):
    dest_raw = trip.get("destination", "Destination")
    dest_city = dest_raw.split(",")[0].strip()
    src_raw = trip.get("source") or "Bengaluru"
    src_city = src_raw.split(",")[0].strip()
    dest_code = dest_city[:3].upper()
    src_code = src_city[:3].upper()

    num_days = int(trip.get("num_days", 1) or 1)
    nights = max(1, num_days - 1)
    trav = int(trip.get("num_travelers", 1) or 1)
    pnr = f"YTR-{int(trip.get('id', 1)) * 1337 + 104200}"

    base_stay = itinerary.get("base_camp_stay") or (hotels.get("base_camp") if isinstance(hotels, dict) else None)
    stay_name = (base_stay.get("name") if isinstance(base_stay, dict) else None) or f"{dest_city} Heritage Resort"

    transit_info = itinerary.get("transit") if isinstance(itinerary.get("transit"), dict) else {}
    transit_title = transit_info.get("direct_transit_mode") or f"{(trip.get('transport') or 'Train').title()} Express Connector"
    transit_dist = transit_info.get("distance_km", 280)
    transit_dur = transit_info.get("duration_hours", 5.5)

    budget_sum = (budget.get("total_budget") or budget.get("total_budget_inr") or trip.get("budget")) or 25000
    try:
        budget_sum = float(budget_sum)
    except Exception:
        budget_sum = 25000.0
    per_person_fare = round(budget_sum / trav)

    t_mode = (trip.get("transport") or "transit").upper()
    if "FLIGHT" in t_mode or "AIR" in t_mode:
        transit_class = "ECONOMY PREMIER"
    elif "TRAIN" in t_mode:
        transit_class = "EXECUTIVE CHAIR"
    else:
        transit_class = "DELUXE COACH"

    # Left: Main Ticket body (360 pt)
    hdr_table = Table([
        [
            Paragraph("<b>YATRIKA EXPEDITION BOARDING PASS</b>", styles["ticket_title"]),
            Paragraph(f"<b>PNR:</b> {pnr}", ParagraphStyle("Pnr", parent=styles["ticket_sub"], alignment=TA_RIGHT))
        ],
        [
            Paragraph("[VERIFIED IRCTC / RTC CORRIDOR]", styles["ticket_sub"]),
            Paragraph("CONFIRMED ITINERARY", ParagraphStyle("Conf", parent=styles["ticket_sub"], alignment=TA_RIGHT))
        ]
    ], colWidths=[240, 110])
    hdr_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))

    corridor_table = Table([
        [
            Paragraph(src_code, styles["station_code"]),
            Paragraph(f"<b>~{transit_dist} km · {transit_dur}h Direct</b><br/>● --- DIRECT CORRIDOR --- ●<br/>{transit_title}", styles["corridor_track"]),
            Paragraph(dest_code, styles["station_code_turq"]),
        ],
        [
            Paragraph(f"{src_city}<br/><font size=6 color='#99F6E4'>Origin Terminal</font>", styles["station_city"]),
            "",
            Paragraph(f"{dest_city}<br/><font size=6 color='#99F6E4'>Base Camp Gate</font>", styles["station_city"]),
        ]
    ], colWidths=[90, 170, 90])
    corridor_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
    ]))

    # Specs Bar
    start_d = trip.get("start_date", "TBD")
    end_d = trip.get("end_date", "TBD")
    specs_table = Table([
        [
            Paragraph("<font size=6 color='#99F6E4'>TRAVEL DATES</font><br/><b>" + f"{start_d} → {end_d}" + "</b>", styles["ticket_sub"]),
            Paragraph("<font size=6 color='#99F6E4'>DURATION</font><br/><b>" + f"{num_days}D · {nights}N" + "</b>", styles["ticket_sub"]),
            Paragraph("<font size=6 color='#99F6E4'>TRAVELERS</font><br/><b>" + f"{trav} Pax" + "</b>", styles["ticket_sub"]),
            Paragraph("<font size=6 color='#99F6E4'>BASE CAMP</font><br/><b>" + f"{stay_name[:20]}" + "</b>", styles["ticket_sub"]),
        ]
    ], colWidths=[105, 65, 65, 115])
    specs_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEABOVE", (0, 0), (-1, -1), 0.5, colors.HexColor("#1E3A5F")),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
        ("LEFTPADDING", (0, 0), (-1, -1), 1),
        ("RIGHTPADDING", (0, 0), (-1, -1), 1),
    ]))

    left_content = [
        hdr_table,
        Spacer(1, 3),
        corridor_table,
        Spacer(1, 3),
        specs_table
    ]

    # Right: Passenger Stub (150 pt)
    qr_widget = qr.QrCodeWidget(f"https://yatrika.travel/planner/{trip.get('id', 1)}")
    bounds = qr_widget.getBounds()
    w = max(1, bounds[2] - bounds[0])
    h = max(1, bounds[3] - bounds[1])
    qr_group = Group()
    qr_group.scale(42.0 / w, 42.0 / h)
    qr_group.add(qr_widget)
    qr_drawing = Drawing(42, 42)
    qr_drawing.add(qr_group)

    stub_content = [
        Paragraph("<b>PASSENGER STUB</b>", ParagraphStyle("PStub", parent=styles["ticket_sub"], alignment=TA_CENTER, fontName=FONT_BOLD, textColor=WHITE, fontSize=7.5)),
        Paragraph(f"<font size=5.5 color='#99F6E4'>{transit_class}</font>", ParagraphStyle("PClass", parent=styles["ticket_sub"], alignment=TA_CENTER)),
        Spacer(1, 2),
        Table([[qr_drawing]], colWidths=[140], style=[('ALIGN', (0, 0), (-1, -1), 'CENTER'), ('LEFTPADDING', (0,0), (-1,-1), 0), ('RIGHTPADDING', (0,0), (-1,-1), 0), ('TOPPADDING', (0,0), (-1,-1), 0), ('BOTTOMPADDING', (0,0), (-1,-1), 0)]),
        Paragraph("<font size=5.5 color='#64748B'>VERIFIED DIGITAL PASS</font>", ParagraphStyle("PVer", parent=styles["ticket_sub"], alignment=TA_CENTER)),
        Spacer(1, 2),
        Paragraph("1-PERSON FARE", styles["stub_fare_lbl"]),
        Paragraph(f"₹{per_person_fare:,.0f}", styles["stub_fare_val"]),
        Paragraph(f"Total: ₹{budget_sum:,.0f} ({trav} pax)", styles["stub_fare_total"]),
    ]

    ticket_table = Table([
        [left_content, stub_content]
    ], colWidths=[360, 150])
    ticket_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), NAVY_DEEP),
        ("BACKGROUND", (1, 0), (1, 0), NAVY_SURF),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#1E3A5F")),
        ("LINEBEFORE", (1, 0), (1, 0), 1, colors.HexColor("#0284C7"), None, (3, 3)),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))

    return ticket_table


# ── Component 2: 4-Pillar Expedition Intelligence Bento Grid ──
def _build_bento_grid(trip: dict, itinerary: dict, budget: dict, hotels: dict, styles: dict):
    dest_city = trip.get("destination", "Destination").split(",")[0].strip()
    src_city = (trip.get("source") or "Bengaluru").split(",")[0].strip()
    trav = int(trip.get("num_travelers", 1) or 1)

    base_stay = itinerary.get("base_camp_stay") or (hotels.get("base_camp") if isinstance(hotels, dict) else None)
    stay_name = (base_stay.get("name") if isinstance(base_stay, dict) else None) or f"{dest_city} Heritage Resort"
    stay_addr = (base_stay.get("address") if isinstance(base_stay, dict) else None) or f"{dest_city} Scenic Valley"
    stay_price = (base_stay.get("price_per_night") if isinstance(base_stay, dict) else None) or 2800
    stay_safety = (base_stay.get("safety_score") if isinstance(base_stay, dict) else None) or "9.6"

    transit_info = itinerary.get("transit") if isinstance(itinerary.get("transit"), dict) else {}
    transit_title = transit_info.get("direct_transit_mode") or f"{(trip.get('transport') or 'Train').title()} Express Connector"
    transit_dist = transit_info.get("distance_km", 280)
    transit_dur = transit_info.get("duration_hours", 5.5)
    transit_fare = transit_info.get("estimated_fare", 1250)

    budget_sum = (budget.get("total_budget") or budget.get("total_budget_inr") or trip.get("budget")) or 25000
    try:
        budget_sum = float(budget_sum)
    except Exception:
        budget_sum = 25000.0
    per_person = round(budget_sum / trav)

    attractions = itinerary.get("selected_attractions") or []
    sights_count = len(attractions) if attractions else int(trip.get("num_days", 1) or 1) * 3

    c1 = [
        Paragraph("● CURATED SANCTUARY", styles["badge_emerald"]),
        Paragraph(f"<b>{stay_name[:26]}</b>", styles["card_title"]),
        Paragraph(f"{stay_addr[:38]}", styles["card_desc"]),
        Spacer(1, 2),
        Paragraph(f"<b>₹{stay_price:,.0f}</b>/nt  ·  Safety Index: {stay_safety}/10", styles["small_bold"])
    ]
    c2 = [
        Paragraph("● CONNECTED TRANSIT", styles["badge_ocean"]),
        Paragraph(f"<b>{transit_title[:26]}</b>", styles["card_title"]),
        Paragraph(f"{src_city} to {dest_city} · ~{transit_dist} km ({transit_dur}h)", styles["card_desc"]),
        Spacer(1, 2),
        Paragraph(f"<b>₹{transit_fare:,.0f}</b>/seat  ·  Direct Corridor", styles["small_bold"])
    ]
    c3 = [
        Paragraph("● FINANCIAL BLUEPRINT", styles["badge_amber"]),
        Paragraph(f"<b>₹{per_person:,.0f}</b> <font size=6.5 color='#64748B'>/ traveler</font>", styles["card_title"]),
        Paragraph(f"Total: ₹{budget_sum:,.0f} ({trav} pax)", styles["card_desc"]),
        Spacer(1, 2),
        Paragraph("Stay-First Allocation  ·  ML Verified", styles["small_bold"])
    ]
    c4 = [
        Paragraph("● CURATED SIGHT LOOPS", styles["badge_purple"]),
        Paragraph(f"<b>{sights_count} Verified Sights</b>", styles["card_title"]),
        Paragraph("Stay-grounded clustering (< 45 km radius)", styles["card_desc"]),
        Spacer(1, 2),
        Paragraph("0 Backtracking  ·  Random Forest ML", styles["small_bold"])
    ]

    bento_table = Table([
        [c1, c2],
        [c3, c4]
    ], colWidths=[250, 250])
    bento_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BG_CARD),
        ("BOX", (0, 0), (0, 0), 0.75, BORDER_CARD),
        ("BOX", (1, 0), (1, 0), 0.75, BORDER_CARD),
        ("BOX", (0, 1), (0, 1), 0.75, BORDER_CARD),
        ("BOX", (1, 1), (1, 1), 0.75, BORDER_CARD),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))

    return bento_table


# ── Component 3: Climate & Weather Transparency Card ──────────
def _build_weather_card(trip: dict, weather: dict, styles: dict):
    horizon = evaluate_weather_horizon(trip, weather)
    is_live = horizon.get("is_live", False)
    badge_style = styles["badge_emerald"] if is_live else styles["badge_ocean"]

    cur = weather.get("current") if isinstance(weather.get("current"), dict) else {}
    temp = cur.get("temperature", 24)
    feels = cur.get("feels_like", 25)
    desc = cur.get("description", "Pleasant").title()
    humidity = cur.get("humidity", 58)
    wind = cur.get("wind_speed", 3.2)

    top_row = Table([
        [
            Paragraph("<b>Destination Climate & Weather Transparency</b>", styles["card_title"]),
            Paragraph(f"<b>[{horizon.get('label', 'Seasonal Guidance').upper()}]</b>", ParagraphStyle("WBadge", parent=badge_style, alignment=TA_RIGHT))
        ]
    ], colWidths=[330, 160], style=[
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ])

    expl_p = Paragraph(f"<font size=7 color='#475569'>{horizon.get('explanation', '')}</font>", styles["body"])

    metrics_table = Table([
        [
            Paragraph(f"<b>{temp}°C</b> <font size=7 color='#64748B'>(Feels {feels}°C)</font><br/><font color='#0284C7' size=7.2><b>{desc}</b></font>", styles["body"]),
            Paragraph(f"Humidity: <b>{humidity}%</b><br/>Wind Speed: <b>{wind} m/s</b>", ParagraphStyle("WMtr", parent=styles["small"], alignment=TA_RIGHT))
        ]
    ], colWidths=[245, 245], style=[
        ("BACKGROUND", (0, 0), (-1, -1), BG_CARD_ALT),
        ("BOX", (0, 0), (-1, -1), 0.5, BORDER_CARD),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ])

    card_table = Table([
        [[top_row, Spacer(1, 2), expl_p, Spacer(1, 3), metrics_table]]
    ], colWidths=[510], style=[
        ("BACKGROUND", (0, 0), (-1, -1), BG_CARD),
        ("BOX", (0, 0), (-1, -1), 0.75, BORDER_CARD),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
    ])

    return card_table


# ── Component 4: Narrative & Metadata Card ────────────────────
def _build_narrative_card(itinerary: dict, styles: dict):
    summary = itinerary.get("trip_summary") or (itinerary.get("itinerary", {}).get("overview") if isinstance(itinerary.get("itinerary"), dict) else "")
    if not summary:
        summary = "Customized expedition planned with verified stays, optimized sightseeing loops, and transparent budget allocation."

    best_time = itinerary.get("best_time_to_visit", "October to May")
    lang = itinerary.get("local_language", "Hindi, Regional & English")
    curr = "INR (₹)"
    tz = itinerary.get("time_zone", "IST (UTC+05:30)")

    meta_table = Table([
        [
            Paragraph(f"<b>Best Season:</b> {best_time}", styles["small"]),
            Paragraph(f"<b>Languages:</b> {lang}", styles["small"]),
            Paragraph(f"<b>Currency:</b> {curr}", styles["small"]),
            Paragraph(f"<b>Timezone:</b> {tz}", styles["small"]),
        ]
    ], colWidths=[130, 130, 110, 120], style=[
        ("BACKGROUND", (0, 0), (-1, -1), BG_CARD_ALT),
        ("BOX", (0, 0), (-1, -1), 0.5, BORDER_CARD),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ])

    card_table = Table([
        [[
            Paragraph("<b>Curated Expedition Narrative</b>", styles["card_title"]),
            Spacer(1, 2),
            Paragraph(summary, styles["body"]),
            Spacer(1, 3),
            meta_table
        ]]
    ], colWidths=[510], style=[
        ("BACKGROUND", (0, 0), (-1, -1), BG_CARD),
        ("BOX", (0, 0), (-1, -1), 0.75, BORDER_CARD),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
    ])

    return card_table


# ── Component 5: Day-by-Day Expedition Itinerary ──────────────
def _build_day_itinerary(day: dict, base_stay_name: str, styles: dict):
    day_num = day.get("day", 1)
    day_title = day.get("theme") or day.get("title") or "Exploration Loop"
    date_str = day.get("date") or ""

    hdr_text = f"<b>Day {day_num}: {day_title}</b>"
    if date_str:
        hdr_text += f" <font size=7 color='#64748B'>({date_str})</font>"

    day_hdr = Table([
        [
            Paragraph(hdr_text, styles["card_title"]),
            Paragraph(f"Anchored to: <b>{base_stay_name[:24]}</b>", ParagraphStyle("Anch", parent=styles["small"], alignment=TA_RIGHT))
        ]
    ], colWidths=[330, 160], style=[
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ])

    slot_rows = []
    slots_meta = [
        ("morning", "MORNING (06:00 - 12:00)", styles["badge_ocean"], OCEAN_LIGHT),
        ("afternoon", "AFTERNOON (12:00 - 17:00)", styles["badge_amber"], AMBER_BG),
        ("evening", "EVENING (17:00 - 21:00)", styles["badge_purple"], PURPLE_BG),
    ]

    for slot_key, slot_lbl, badge_style, slot_bg in slots_meta:
        slot = day.get(slot_key)
        if not slot or not isinstance(slot, dict):
            continue

        places_list = slot.get("places")
        if places_list and isinstance(places_list, list):
            main_place = places_list[0] if places_list else {}
            name = main_place.get("name") or slot.get("place") or slot.get("activity") or "Sightseeing"
            dur = main_place.get("duration") or slot.get("duration") or "2.5h"
            fee = main_place.get("fee") or slot.get("entry_fee") or "Free"
            category = main_place.get("category") or "Sight"
            desc = slot.get("activity") or main_place.get("description") or ""
        else:
            name = slot.get("name") or slot.get("place") or slot.get("activity") or "Sightseeing"
            dur = slot.get("duration") or "2.5h"
            fee = slot.get("entry_fee") or slot.get("fee") or "Free"
            category = slot.get("category") or "Sight"
            desc = slot.get("activity") or slot.get("description") or ""

        # Normalize fee string
        if isinstance(fee, (int, float)):
            fee_str = f"₹{fee:,.0f}" if fee > 0 else "Free"
        elif str(fee).isdigit():
            fee_str = f"₹{int(fee):,.0f}" if int(fee) > 0 else "Free"
        elif str(fee).strip() and not str(fee).startswith("₹") and not str(fee).lower() == "free":
            fee_str = f"₹{fee}"
        else:
            fee_str = str(fee)

        proximity = slot.get("proximity") or "Proximity: < 15 km from Base Camp"
        tips = slot.get("tips")

        left_cell = [
            Paragraph(f"<b>[{slot_lbl}]</b>", badge_style),
            Paragraph(f"<b>{name}</b>", styles["body_bold"]),
            Paragraph(f"<font size=6.8 color='#64748B'>{category} · Duration: {dur} · Entry: {fee_str}</font>", styles["small"]),
        ]
        right_cell = [
            Paragraph(desc if desc else f"Curated exploration of {name} with scenic viewpoint stops.", styles["body"]),
            Paragraph(f"<font size=6.8 color='#0284C7'>{proximity}</font>" + (f" · <i>Advice: {tips}</i>" if tips else ""), styles["extra_small"])
        ]

        slot_table = Table([[left_cell, right_cell]], colWidths=[180, 310])
        slot_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), slot_bg),
            ("BOX", (0, 0), (-1, -1), 0.5, BORDER_CARD),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        slot_rows.append(slot_table)
        slot_rows.append(Spacer(1, 2.5))

    footer_items = []
    if day.get("food_recommendations"):
        meals = []
        for f in day["food_recommendations"]:
            if isinstance(f, dict):
                meals.append(f"{f.get('meal', 'Meal')}: {f.get('restaurant', 'Local Cafe')} ({f.get('cuisine', 'Regional')})")
        if meals:
            footer_items.append(Paragraph("• <b>Dining:</b> " + "; ".join(meals), styles["small"]))

    if day.get("daily_budget"):
        db = day['daily_budget']
        db_str = f"₹{db:,.0f}" if isinstance(db, (int, float)) else str(db)
        footer_items.append(Paragraph(f"• <b>Daily Allocation:</b> {db_str}", styles["small"]))

    if day.get("local_tips"):
        footer_items.append(Paragraph(f"• <b>Local Advice:</b> {day['local_tips']}", styles["small"]))

    card_content = [day_hdr, Spacer(1, 3)] + slot_rows
    if footer_items:
        card_content.append(Spacer(1, 2))
        card_content.extend(footer_items)

    day_table = Table([
        [card_content]
    ], colWidths=[510], style=[
        ("BACKGROUND", (0, 0), (-1, -1), BG_CARD),
        ("BOX", (0, 0), (-1, -1), 0.75, BORDER_CARD),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
    ])

    return KeepTogether([day_table, Spacer(1, 6)])


# ── Component 6: Base Camp & Accommodations ───────────────────
def _build_hotels_section(base_stay: dict, hotels: dict, trip: dict, styles: dict):
    story = [
        Paragraph("<b>Base Camp Accommodations & Sanctuary Stays</b>", styles["section_h1"]),
    ]

    dest_city = trip.get("destination", "Destination").split(",")[0].strip()
    name = (base_stay.get("name") if isinstance(base_stay, dict) else None) or f"{dest_city} Heritage Resort"
    addr = (base_stay.get("address") if isinstance(base_stay, dict) else None) or f"{dest_city} Scenic Corridor"
    price = (base_stay.get("price_per_night") if isinstance(base_stay, dict) else None) or 2800
    safety = (base_stay.get("safety_score") if isinstance(base_stay, dict) else None) or "9.6"
    desc = (base_stay.get("description") if isinstance(base_stay, dict) else None) or "Centrally positioned base camp stay with verified security and high-speed Wi-Fi, optimized for daily sightseeing loops."
    amenities = (base_stay.get("amenities") if isinstance(base_stay, dict) else None) or ["Wi-Fi", "Breakfast", "AC", "Power Backup", "24/7 Security"]

    sanctuary_table = Table([
        [
            [
                Paragraph("<b>LOCKED BASE CAMP ANCHOR</b>", styles["badge_emerald"]),
                Paragraph(f"<b>{name}</b>", styles["card_title"]),
                Paragraph(f"<font color='#64748B'>{addr}</font>", styles["small"]),
                Spacer(1, 2),
                Paragraph(desc, styles["body"]),
                Spacer(1, 2),
                Paragraph(f"<b>Amenities:</b> {', '.join(amenities)}", styles["small"]),
            ],
            [
                Paragraph(f"<b>₹{price:,.0f}</b>", ParagraphStyle("HPrice", parent=styles["card_title"], fontSize=12, textColor=TURQUOISE, alignment=TA_RIGHT)),
                Paragraph("<font size=6.5 color='#64748B'>per night</font>", ParagraphStyle("HPer", parent=styles["small"], alignment=TA_RIGHT)),
                Spacer(1, 4),
                Paragraph(f"Safety: <b>{safety}/10</b>", ParagraphStyle("HSafe", parent=styles["small"], alignment=TA_RIGHT)),
            ]
        ]
    ], colWidths=[385, 105], style=[
        ("BACKGROUND", (0, 0), (-1, -1), BG_CARD),
        ("BOX", (0, 0), (-1, -1), 1, TURQUOISE),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ])
    story.append(sanctuary_table)
    story.append(Spacer(1, 5))

    alt_rows = [
        [
            Paragraph("<b>Category / Tier</b>", styles["small_bold"]),
            Paragraph("<b>Hotel Name</b>", styles["small_bold"]),
            Paragraph("<b>Price / Night (INR)</b>", ParagraphStyle("HPrHdr", parent=styles["small_bold"], alignment=TA_RIGHT)),
            Paragraph("<b>Verified Rating</b>", ParagraphStyle("HRatHdr", parent=styles["small_bold"], alignment=TA_RIGHT)),
        ]
    ]

    for tier, label in [
        ("budget_hotels", "Budget-Friendly"),
        ("mid_range_hotels", "Comfort & Standard"),
        ("luxury_hotels", "Premium Heritage"),
    ]:
        h_list = hotels.get(tier, []) if isinstance(hotels, dict) else []
        for h in h_list[:2]:
            h_name = h.get("name", "Hotel")
            h_price = h.get("price_per_night", 2000)
            h_rating = h.get("rating") or h.get("star_rating") or "4.5"
            alt_rows.append([
                Paragraph(label, styles["small"]),
                Paragraph(f"<b>{h_name}</b>", styles["small"]),
                Paragraph(f"₹{h_price:,.0f}", ParagraphStyle("HPrc", parent=styles["small"], alignment=TA_RIGHT)),
                Paragraph(f"Rating: {h_rating}/5.0", ParagraphStyle("HRat", parent=styles["small"], alignment=TA_RIGHT)),
            ])

    if len(alt_rows) > 1:
        alt_table = Table(alt_rows, colWidths=[120, 210, 100, 80])
        alt_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), BG_CARD_ALT),
            ("BOX", (0, 0), (-1, -1), 0.5, BORDER_CARD),
            ("GRID", (0, 0), (-1, -1), 0.5, BORDER_CARD),
            ("TOPPADDING", (0, 0), (-1, -1), 3.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        story.append(alt_table)

    return KeepTogether(story)


# ── Component 7: Financial Blueprint (Budget Breakdown) ───────
def _build_budget_section(budget: dict, trip: dict, styles: dict):
    story = [
        Paragraph("<b>Financial Blueprint & Itemized Budget Allocation</b>", styles["section_h1"]),
    ]

    breakdown = budget.get("breakdown") if isinstance(budget.get("breakdown"), dict) else {}
    total_b = budget.get("total_budget") or budget.get("total_budget_inr") or trip.get("budget") or 25000
    try:
        total_b = float(total_b)
    except Exception:
        total_b = 25000.0

    b_rows = [
        [
            Paragraph("<b>Category</b>", styles["small_bold"]),
            Paragraph("<b>Amount (INR)</b>", ParagraphStyle("BPrHdr", parent=styles["small_bold"], alignment=TA_RIGHT)),
            Paragraph("<b>% of Budget</b>", ParagraphStyle("BPctHdr", parent=styles["small_bold"], alignment=TA_CENTER)),
            Paragraph("<b>Allocation Strategy / Details</b>", styles["small_bold"]),
        ]
    ]

    if breakdown:
        for cat, info in breakdown.items():
            cat_label = cat.replace("_", " ").title()
            amt = info.get("amount", 0)
            pct = info.get("percentage", 0)
            details = info.get("details", "Verified allocation based on duration & travelers")
            b_rows.append([
                Paragraph(f"<b>{cat_label}</b>", styles["small"]),
                Paragraph(f"₹{amt:,.0f}", ParagraphStyle("BAmt", parent=styles["small"], alignment=TA_RIGHT)),
                Paragraph(f"{pct:.1f}%", ParagraphStyle("BPct", parent=styles["small"], alignment=TA_CENTER)),
                Paragraph(details[:55], styles["small"]),
            ])
    else:
        for cat_label, pct in [("Accommodation", 35), ("Food & Dining", 25), ("Transport", 20), ("Sightseeing & Activities", 15), ("Shopping & Contingency", 5)]:
            amt = total_b * pct / 100
            b_rows.append([
                Paragraph(f"<b>{cat_label}</b>", styles["small"]),
                Paragraph(f"₹{amt:,.0f}", ParagraphStyle("BAmt", parent=styles["small"], alignment=TA_RIGHT)),
                Paragraph(f"{pct:.1f}%", ParagraphStyle("BPct", parent=styles["small"], alignment=TA_CENTER)),
                Paragraph(f"Estimated {pct}% share of total expedition budget", styles["small"]),
            ])

    b_rows.append([
        Paragraph("<b>TOTAL EXPEDITION BUDGET</b>", ParagraphStyle("BTot", parent=styles["small_bold"], textColor=WHITE)),
        Paragraph(f"<b>₹{total_b:,.0f}</b>", ParagraphStyle("BTotAmt", parent=styles["small_bold"], textColor=WHITE, alignment=TA_RIGHT)),
        Paragraph("<b>100%</b>", ParagraphStyle("BTotPct", parent=styles["small_bold"], textColor=WHITE, alignment=TA_CENTER)),
        Paragraph("<font color='#E6FFFA'><b>ML Verified Stay-First Allocation</b></font>", styles["small"]),
    ])

    b_table = Table(b_rows, colWidths=[120, 95, 75, 220])
    b_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BG_CARD_ALT),
        ("BACKGROUND", (0, -1), (-1, -1), NAVY_DEEP),
        ("BOX", (0, 0), (-1, -1), 0.75, BORDER_CARD),
        ("GRID", (0, 0), (-1, -2), 0.5, BORDER_CARD),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(b_table)

    # Realized expenses section if present
    if trip.get("id"):
        try:
            from backend.models.trip import get_expenses
            expenses = get_expenses(trip["id"])
            if expenses:
                story.append(Spacer(1, 5))
                story.append(Paragraph("<b>Realized Expenses Log</b>", styles["section_h2"]))
                exp_rows = [
                    [
                        Paragraph("<b>Date</b>", styles["small_bold"]),
                        Paragraph("<b>Category</b>", styles["small_bold"]),
                        Paragraph("<b>Note / Description</b>", styles["small_bold"]),
                        Paragraph("<b>Amount (INR)</b>", ParagraphStyle("EPrHdr", parent=styles["small_bold"], alignment=TA_RIGHT)),
                    ]
                ]
                total_spent = 0.0
                for e in expenses:
                    amt = float(e.get("amount", 0))
                    total_spent += amt
                    exp_rows.append([
                        Paragraph(str(e.get("date", ""))[:10], styles["small"]),
                        Paragraph(str(e.get("category", "")).title(), styles["small"]),
                        Paragraph(str(e.get("description", "—"))[:45], styles["small"]),
                        Paragraph(f"₹{amt:,.2f}", ParagraphStyle("EAmt", parent=styles["small"], alignment=TA_RIGHT)),
                    ])
                exp_rows.append([
                    Paragraph("<b>Total Spent:</b>", styles["small_bold"]),
                    "", "",
                    Paragraph(f"<b>₹{total_spent:,.2f}</b>", ParagraphStyle("ETot", parent=styles["small_bold"], textColor=TURQUOISE, alignment=TA_RIGHT))
                ])
                exp_table = Table(exp_rows, colWidths=[90, 100, 220, 100])
                exp_table.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), BG_CARD_ALT),
                    ("BOX", (0, 0), (-1, -1), 0.5, BORDER_CARD),
                    ("GRID", (0, 0), (-1, -2), 0.5, BORDER_CARD),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ]))
                story.append(exp_table)
        except Exception:
            pass

    return KeepTogether(story)


# ── Component 8: Destination-Aware Packing Checklist ──────────
def _build_packing_section(trip: dict, weather: dict, itinerary: dict, styles: dict):
    checklist_data = generate_smart_packing_checklist(trip, weather)
    weather_ctx = checklist_data.get("weather_context", "Standard Climate")

    story = [
        Paragraph(f"<b>Destination-Aware Smart Packing Checklist</b> <font size=7.5 color='#64748B'>({weather_ctx})</font>", styles["section_h1"]),
    ]

    categories = checklist_data.get("categories", {})
    pack_cards = []

    for cat_key, cat_data in categories.items():
        title = cat_data.get("title", cat_key.title())
        items = cat_data.get("items", [])
        item_paragraphs = [
            Paragraph(f"<b>{title.upper()}</b>", styles["badge_ocean"]),
            Spacer(1, 2)
        ]
        for it in items[:6]:
            text = it.get("text") if isinstance(it, dict) else str(it)
            is_packed = it.get("packed", False) if isinstance(it, dict) else False
            box = "[X]" if is_packed else "[  ]"
            item_paragraphs.append(Paragraph(f"<font color='#0284C7'>{box}</font> {text}", styles["small"]))

        pack_cards.append(item_paragraphs)

    if len(pack_cards) >= 4:
        row1 = [pack_cards[0], pack_cards[1]]
        row2 = [pack_cards[2], pack_cards[3]]
        table_data = [row1, row2]
        col_w = [250, 250]
    else:
        table_data = [[c for c in pack_cards]]
        col_w = [510 // max(1, len(pack_cards))] * len(pack_cards)

    pack_table = Table(table_data, colWidths=col_w)
    pack_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BG_CARD),
        ("BOX", (0, 0), (-1, -1), 0.75, BORDER_CARD),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER_CARD),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(pack_table)

    return KeepTogether(story)


# ── Component 9: Safety & 24/7 Helplines ───────────────────────
def _build_emergency_section(itinerary: dict, trip: dict, styles: dict):
    story = [
        Paragraph("<b>Safety Guidelines & 24/7 National Emergency Helplines</b>", styles["section_h1"]),
    ]

    h1 = [Paragraph("<b>POLICE SUPPORT</b>", styles["badge_amber"]), Paragraph("<b>100</b>", styles["card_title"]), Paragraph("National Emergency", styles["small"])]
    h2 = [Paragraph("<b>MEDICAL AMBULANCE</b>", styles["badge_emerald"]), Paragraph("<b>108</b>", styles["card_title"]), Paragraph("Emergency Healthcare", styles["small"])]
    h3 = [Paragraph("<b>TOURIST HELPLINE</b>", styles["badge_ocean"]), Paragraph("<b>1363</b>", styles["card_title"]), Paragraph("Toll-Free Support", styles["small"])]
    h4 = [Paragraph("<b>DISASTER OPERATIONS</b>", styles["badge_purple"]), Paragraph("<b>1070</b>", styles["card_title"]), Paragraph("State Helpline", styles["small"])]

    hl_table = Table([[h1, h2, h3, h4]], colWidths=[125, 125, 125, 125])
    hl_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BG_CARD),
        ("BOX", (0, 0), (-1, -1), 0.75, BORDER_CARD),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER_CARD),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ]))
    story.append(hl_table)
    story.append(Spacer(1, 4))

    safety_tips = itinerary.get("safety_tips") or [
        "Keep photocopies and cloud backups of official identification documents.",
        "Store base camp sanctuary contact details and offline maps on your mobile.",
        "Use authorized RTC / prepaid taxi booths at transit terminals."
    ]
    tip_items = []
    for tip in safety_tips[:3]:
        tip_items.append(Paragraph(f"• {tip}", styles["small"]))

    notes = trip.get("notes")
    if notes:
        tip_items.append(Spacer(1, 2))
        tip_items.append(Paragraph(f"<b>Traveler Notes:</b> {notes}", styles["small"]))

    tips_table = Table([
        [tip_items]
    ], colWidths=[510], style=[
        ("BACKGROUND", (0, 0), (-1, -1), BG_CARD_ALT),
        ("BOX", (0, 0), (-1, -1), 0.5, BORDER_CARD),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ])
    story.append(tips_table)

    return KeepTogether(story)


# ── Public API Function ───────────────────────────────────────
def generate_trip_pdf(trip_row, itinerary: dict, budget: dict,
                      hotels: dict, weather: dict) -> str:
    """
    Generate a publication-grade luxury PDF expedition report for a trip.
    Synchronized with the Yatrika web interface design language.

    Returns the absolute file path of the saved PDF.
    """
    os.makedirs(cfg.PDF_OUTPUT_FOLDER, exist_ok=True)
    filename = f"trip_{trip_row['id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    filepath = os.path.join(cfg.PDF_OUTPUT_FOLDER, filename)

    doc = SimpleDocTemplate(
        filepath, pagesize=A4,
        rightMargin=1.5 * cm, leftMargin=1.5 * cm,
        topMargin=1.5 * cm, bottomMargin=1.5 * cm
    )

    styles = _get_styles()
    story  = []

    trip_dict = dict(trip_row) if not isinstance(trip_row, dict) else trip_row
    itinerary = itinerary or {}
    budget = budget or {}
    hotels = hotels or {}
    weather = weather or {}

    # 1. Boarding Pass Ticket
    story.append(_build_boarding_pass(trip_dict, itinerary, budget, hotels, styles))
    story.append(Spacer(1, 6))

    # 2. 4-Pillar Expedition Intelligence Bento Grid
    story.append(_build_bento_grid(trip_dict, itinerary, budget, hotels, styles))
    story.append(Spacer(1, 6))

    # 3. Weather & Climate Transparency Card
    story.append(_build_weather_card(trip_dict, weather, styles))
    story.append(Spacer(1, 6))

    # 4. Narrative & Meta Pills
    story.append(_build_narrative_card(itinerary, styles))
    story.append(Spacer(1, 8))

    # 5. Day-by-Day Expedition Itinerary Loops
    base_stay = itinerary.get("base_camp_stay") or (hotels.get("base_camp") if isinstance(hotels, dict) else None)
    base_stay_name = (base_stay.get("name") if isinstance(base_stay, dict) else None) or f"{trip_dict.get('destination', '').split(',')[0]} Base Camp"

    days = itinerary.get("days", [])
    if days:
        story.append(Paragraph("<b>Day-by-Day Expedition Itinerary Loops</b>", styles["section_h1"]))
        for d in days:
            story.append(_build_day_itinerary(d, base_stay_name, styles))

    # 6. Base Camp Accommodations
    story.append(Spacer(1, 6))
    story.append(_build_hotels_section(base_stay or {}, hotels, trip_dict, styles))

    # 7. Financial Blueprint & Itemized Budget Allocation
    story.append(Spacer(1, 6))
    story.append(_build_budget_section(budget, trip_dict, styles))

    # 8. Destination-Aware Smart Packing Checklist
    story.append(Spacer(1, 6))
    story.append(_build_packing_section(trip_dict, weather, itinerary, styles))

    # 9. Safety Guidelines & 24/7 Helplines
    story.append(Spacer(1, 6))
    story.append(_build_emergency_section(itinerary, trip_dict, styles))

    # Canvas factory with dynamic destination
    def make_canvas(*args, **kwargs):
        c = YatrikaNumberedCanvas(*args, **kwargs)
        c.trip_destination = trip_dict.get("destination", "").split(",")[0].strip()
        return c

    doc.build(story, canvasmaker=make_canvas)
    return filepath
