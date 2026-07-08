"""
TravelPlannerAgent - PDF Generator Service
Generates a comprehensive PDF travel report using ReportLab.
"""

import os
import json
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from backend.config import get_config

cfg = get_config()


# ── Color palette ─────────────────────────────────────────────
IBM_BLUE   = colors.HexColor("#0062FF")
IBM_DARK   = colors.HexColor("#161616")
IBM_LIGHT  = colors.HexColor("#F4F4F4")
IBM_BORDER = colors.HexColor("#E0E0E0")
ACCENT     = colors.HexColor("#0043CE")


def _get_styles() -> dict:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "Title", parent=base["Title"],
            textColor=IBM_DARK, fontSize=24, spaceAfter=6,
            alignment=TA_CENTER
        ),
        "subtitle": ParagraphStyle(
            "Subtitle", parent=base["Normal"],
            textColor=IBM_BLUE, fontSize=13, spaceAfter=4,
            alignment=TA_CENTER
        ),
        "h1": ParagraphStyle(
            "H1", parent=base["Heading1"],
            textColor=IBM_BLUE, fontSize=14, spaceBefore=12, spaceAfter=4
        ),
        "h2": ParagraphStyle(
            "H2", parent=base["Heading2"],
            textColor=ACCENT, fontSize=12, spaceBefore=8, spaceAfter=3
        ),
        "body": ParagraphStyle(
            "Body", parent=base["Normal"],
            fontSize=10, leading=16, spaceAfter=4
        ),
        "bullet": ParagraphStyle(
            "Bullet", parent=base["Normal"],
            fontSize=10, leading=15, leftIndent=16, bulletIndent=8
        ),
        "small": ParagraphStyle(
            "Small", parent=base["Normal"],
            fontSize=8, textColor=colors.gray
        ),
        "center": ParagraphStyle(
            "Center", parent=base["Normal"],
            fontSize=10, alignment=TA_CENTER
        ),
    }


def generate_trip_pdf(trip_row, itinerary: dict, budget: dict,
                      hotels: dict, weather: dict) -> str:
    """
    Generate a full-featured PDF report for a trip.

    Returns the absolute file path of the saved PDF.
    """
    os.makedirs(cfg.PDF_OUTPUT_FOLDER, exist_ok=True)
    filename = f"trip_{trip_row['id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    filepath = os.path.join(cfg.PDF_OUTPUT_FOLDER, filename)

    doc = SimpleDocTemplate(
        filepath, pagesize=A4,
        rightMargin=2 * cm, leftMargin=2 * cm,
        topMargin=2 * cm, bottomMargin=2 * cm
    )

    styles = _get_styles()
    story  = []

    # ── Cover ─────────────────────────────────────────────────
    story.append(Spacer(1, 1.5 * cm))
    story.append(Paragraph("✈ AI Travel Planner", styles["title"]))
    story.append(Paragraph(
        f"Trip Report: <b>{trip_row['destination']}</b>",
        styles["subtitle"]
    ))
    story.append(Spacer(1, 0.4 * cm))

    cover_data = [
        ["Destination", trip_row["destination"]],
        ["Travel Dates", f"{trip_row['start_date']}  →  {trip_row['end_date']}"],
        ["Duration",     f"{trip_row['num_days']} days"],
        ["Travelers",    str(trip_row["num_travelers"])],
        ["Budget",       f"USD {trip_row['budget']:,.0f}"],
        ["Travel Style", trip_row["travel_style"].title()],
        ["Generated",    datetime.now().strftime("%d %B %Y, %H:%M")],
    ]
    table = Table(cover_data, colWidths=[5 * cm, 11 * cm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), IBM_LIGHT),
        ("TEXTCOLOR",  (0, 0), (0, -1), IBM_DARK),
        ("FONTNAME",   (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE",   (0, 0), (-1, -1), 10),
        ("ROWBACKGROUNDS", (1, 0), (-1, -1), [colors.white, IBM_LIGHT]),
        ("GRID",       (0, 0), (-1, -1), 0.5, IBM_BORDER),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING",  (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(table)
    story.append(Spacer(1, 0.6 * cm))
    story.append(HRFlowable(width="100%", thickness=1, color=IBM_BLUE))
    story.append(Spacer(1, 0.5 * cm))

    # ── Trip Summary ──────────────────────────────────────────
    if itinerary.get("trip_summary"):
        story.append(Paragraph("Trip Overview", styles["h1"]))
        story.append(Paragraph(itinerary["trip_summary"], styles["body"]))
        story.append(Spacer(1, 0.3 * cm))

        meta_items = []
        for key in ["best_time_to_visit", "local_language", "currency", "time_zone"]:
            val = itinerary.get(key, "—")
            if val:
                label = key.replace("_", " ").title()
                meta_items.append(f"<b>{label}:</b> {val}")
        for item in meta_items:
            story.append(Paragraph(f"• {item}", styles["bullet"]))
        story.append(Spacer(1, 0.4 * cm))

    # ── Day-wise Itinerary ────────────────────────────────────
    story.append(Paragraph("Day-wise Itinerary", styles["h1"]))
    for day in itinerary.get("days", []):
        day_title = f"Day {day.get('day', '?')} — {day.get('date', '')}  |  {day.get('theme', '')}"
        story.append(Paragraph(day_title, styles["h2"]))

        for period in ["morning", "afternoon", "evening"]:
            slot = day.get(period)
            if slot:
                places_list = slot.get("places", [])
                if places_list:
                    for pl in places_list:
                        story.append(Paragraph(
                            f"<b>{period.title()}:</b> {pl.get('icon', '📍')} {pl.get('name', '—')} "
                            f"<i>({pl.get('category', '')})</i> — "
                            f"{pl.get('duration', '')} | Entry: {pl.get('fee', 'Free')}",
                            styles["body"]
                        ))
                else:
                    story.append(Paragraph(
                        f"<b>{period.title()}:</b> {slot.get('activity', '—')} "
                        f"<i>({slot.get('place', '')})</i> — "
                        f"{slot.get('duration', '')} | Entry: {slot.get('entry_fee', 'Free')}",
                        styles["body"]
                    ))
                if slot.get("tips"):
                    story.append(Paragraph(f"  💡 {slot['tips']}", styles["small"]))

        if day.get("food_recommendations"):
            meals = "; ".join(
                f"{f['meal']}: {f['restaurant']} ({f['cuisine']}, {f['price_range']})"
                for f in day["food_recommendations"]
            )
            story.append(Paragraph(f"<b>Food:</b> {meals}", styles["body"]))

        if day.get("daily_budget"):
            story.append(Paragraph(
                f"<b>Daily Budget:</b> USD {day['daily_budget']:,}",
                styles["body"]
            ))

        if day.get("local_tips"):
            story.append(Paragraph(f"<b>Local Tip:</b> {day['local_tips']}", styles["body"]))

        story.append(Spacer(1, 0.3 * cm))

    # ── Budget Breakdown ──────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=0.5, color=IBM_BORDER))
    story.append(Paragraph("Budget Breakdown", styles["h1"]))
    if budget.get("breakdown"):
        budget_rows = [["Category", "Amount (USD)", "% of Budget", "Details"]]
        for cat, info in budget["breakdown"].items():
            budget_rows.append([
                cat.replace("_", " ").title(),
                f"${info.get('amount', 0):,.0f}",
                f"{info.get('percentage', 0):.1f}%",
                info.get("details", "—")[:60]
            ])
        budget_rows.append([
            "TOTAL", f"${budget.get('total_budget', 0):,.0f}", "100%", ""
        ])
        bt = Table(budget_rows, colWidths=[4 * cm, 3 * cm, 3 * cm, 7 * cm])
        bt.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), IBM_BLUE),
            ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
            ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",   (0, 0), (-1, -1), 9),
            ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, IBM_LIGHT]),
            ("BACKGROUND", (0, -1), (-1, -1), ACCENT),
            ("TEXTCOLOR",  (0, -1), (-1, -1), colors.white),
            ("FONTNAME",   (0, -1), (-1, -1), "Helvetica-Bold"),
            ("GRID",       (0, 0), (-1, -1), 0.5, IBM_BORDER),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING",  (0, 0), (-1, -1), 5),
        ]))
        story.append(bt)
        story.append(Spacer(1, 0.4 * cm))

    # ── Hotels ────────────────────────────────────────────────
    story.append(Paragraph("Hotel Recommendations", styles["h1"]))
    for category in ["budget_hotels", "mid_range_hotels", "luxury_hotels"]:
        label = category.replace("_", " ").title()
        hotel_list = hotels.get(category, [])
        if hotel_list:
            story.append(Paragraph(label, styles["h2"]))
            for h in hotel_list[:3]:
                story.append(Paragraph(
                    f"<b>{h.get('name', '—')}</b>  |  "
                    f"${h.get('price_per_night', 0)}/night  |  "
                    f"Rating: {h.get('rating', '—')}★  |  "
                    f"Distance: {h.get('distance_from_center', '—')}",
                    styles["body"]
                ))
                amenities = ", ".join(h.get("amenities", []))
                if amenities:
                    story.append(Paragraph(f"  Amenities: {amenities}", styles["small"]))
            story.append(Spacer(1, 0.2 * cm))

    # ── Packing Checklist ─────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=0.5, color=IBM_BORDER))
    packing = itinerary.get("packing_checklist", {})
    if packing:
        story.append(Paragraph("Packing Checklist", styles["h1"]))
        pack_data = []
        for category, items in packing.items():
            if items:
                pack_data.append([
                    category.replace("_", " ").title(),
                    " • ".join(items)
                ])
        if pack_data:
            pack_table = Table(pack_data, colWidths=[5 * cm, 12 * cm])
            pack_table.setStyle(TableStyle([
                ("BACKGROUND",  (0, 0), (0, -1), IBM_LIGHT),
                ("FONTNAME",    (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE",    (0, 0), (-1, -1), 9),
                ("GRID",        (0, 0), (-1, -1), 0.5, IBM_BORDER),
                ("VALIGN",      (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING",  (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ]))
            story.append(pack_table)
        story.append(Spacer(1, 0.4 * cm))

    # ── Safety & Emergency ────────────────────────────────────
    if itinerary.get("safety_tips") or itinerary.get("emergency_numbers"):
        story.append(Paragraph("Safety & Emergency", styles["h1"]))
        for tip in itinerary.get("safety_tips", []):
            story.append(Paragraph(f"• {tip}", styles["bullet"]))
        emg = itinerary.get("emergency_numbers", {})
        if emg:
            story.append(Paragraph(
                f"Emergency Numbers — Police: {emg.get('police', '—')} | "
                f"Ambulance: {emg.get('ambulance', '—')} | "
                f"Tourist Helpline: {emg.get('tourist_helpline', '—')}",
                styles["body"]
            ))

    # ── Footer ────────────────────────────────────────────────
    story.append(Spacer(1, 1 * cm))
    story.append(HRFlowable(width="100%", thickness=1, color=IBM_BORDER))
    story.append(Paragraph(
        "Generated by AI Travel Planner Agent  |  Powered by IBM Granite & IBM watsonx.ai  |  ",
        styles["small"]
    ))

    doc.build(story)
    return filepath
