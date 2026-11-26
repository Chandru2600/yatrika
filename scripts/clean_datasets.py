"""
Pan-India Dataset Hygiene Script.
Cleans:
1. FACULTY_EVALUATION_DATASETS/1_All_India_Tourist_Attractions_10025.csv:
   - Removes statue life-dates (e.g. 'Rajiv Gandhi 1944-91'), garbled codes ('40rp'),
     ASI numbered placeholders, and unverified OSM artifacts.
   - Deduplicates by normalized (name, city).
2. FACULTY_EVALUATION_DATASETS/2_All_India_Hotels_and_Accommodations_150000.csv:
   - Fixes wrong Mysuru PIN 561006 -> 570001.
   - Drops rows with empty property names.
"""

import csv
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
ATT_CSV = BASE_DIR / "FACULTY_EVALUATION_DATASETS" / "1_All_India_Tourist_Attractions_10025.csv"
HOT_CSV = BASE_DIR / "FACULTY_EVALUATION_DATASETS" / "2_All_India_Hotels_and_Accommodations_150000.csv"

BARE_GENERIC = {
    "temple", "church", "mosque", "masjid", "park", "lake", "falls", "waterfall",
    "waterfalls", "hill", "hills", "fort", "palace", "museum", "beach", "garden",
    "viewpoint", "view point", "peak", "cave", "bridge", "dam", "statue", "gate",
}


def is_junk_attraction(name: str) -> bool:
    if not name or len(name.strip()) < 3:
        return True
    s = name.strip()
    if re.search(r"(?i)ASI Monument|Monument\s*#|#\d+|Protected Heritage|ASI Protected|Protected Site", s):
        return True
    if re.match(r"^[\d\s\-_#]+$", s) or re.match(r"^\d+[A-Za-z\-_]+$", s) or re.match(r"^[A-Za-z0-9\-_]{1,4}$", s):
        return True
    if re.search(r"(?i)\b(?:H#|St\s*\d+|G\d+-\d+|Market ID|Plot No|Sector\s*\d+|Bus Stop|Traffic Signal|Police Station)\b", s):
        return True
    if re.search(r"\b(?:18|19|20)\d{2}\s*[-–]\s*\d{2,4}\b", s) or re.search(r"(?i)\b\d+rp\b", s):
        return True
    if len(s) > 55 or re.search(r"(?i)\b(?:to the (?:east|west|north|south) of|for climbers)\b", s):
        return True
    if any(b in s.lower() for b in ("cave of nightmares", "in my dream", "locomotive works", "free view point", "cliff jumping point", "temple elephant bathing", "sunset viewpoint with")):
        return True
    if s.lower() in BARE_GENERIC:
        return True
    return False


def clean_attractions():
    if not ATT_CSV.exists():
        return 0, 0
    with open(ATT_CSV, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames
        rows = list(reader)

    kept = []
    seen = set()
    for r in rows:
        nm = (r.get("Name") or "").strip()
        if is_junk_attraction(nm):
            continue
        city = (r.get("City") or "").strip().lower()
        key = (re.sub(r"[^a-z0-9]", "", nm.lower()), city)
        if key in seen:
            continue
        seen.add(key)
        kept.append(r)

    with open(ATT_CSV, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(kept)
    return len(rows), len(kept)


def clean_hotels():
    if not HOT_CSV.exists():
        return 0, 0
    with open(HOT_CSV, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames
        rows = list(reader)

    kept = []
    fixed_pins = 0
    for r in rows:
        name = (r.get("property_name") or "").strip()
        if len(name) < 3:
            continue
        city = (r.get("city") or "").lower()
        addr = r.get("address") or ""
        pin = r.get("pincode") or ""
        if ("mysur" in city or "mysor" in city or "mysur" in addr.lower()) and ("561006" in addr or "561006" in pin):
            r["address"] = addr.replace("561006", "570001")
            r["pincode"] = pin.replace("561006", "570001")
            fixed_pins += 1
        kept.append(r)

    with open(HOT_CSV, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(kept)
    return len(rows), fixed_pins


if __name__ == "__main__":
    a_before, a_after = clean_attractions()
    h_total, h_pins = clean_hotels()
    print(f"Attractions: {a_before} -> {a_after} (removed {a_before - a_after})")
    print(f"Hotels: {h_total} rows, fixed {h_pins} Mysuru 561006 PINs")
