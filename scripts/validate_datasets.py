#!/usr/bin/env python3
"""
Yatrika Travel Agent - Dataset Validation & Integrity Auditing Tool
Audits All-India Tourist Attractions (10,025) and Accommodations (150,000) datasets
for stale/invalid rows, coordinate boundary violations, missing operating hours,
non-positive prices, and schema anomalies.
"""

import os
import sys
import csv
import pandas as pd
from pathlib import Path
from datetime import datetime, date

BASE_DIR = Path(__file__).resolve().parent.parent
DATASETS_DIR = BASE_DIR / "FACULTY_EVALUATION_DATASETS"

# Geographic boundary for mainland India + islands
INDIA_LAT_MIN, INDIA_LAT_MAX = 6.0, 38.0
INDIA_LON_MIN, INDIA_LON_MAX = 68.0, 98.0


def validate_attractions_dataset(csv_path: Path) -> dict:
    """Validates 1_All_India_Tourist_Attractions_10025.csv."""
    stats = {
        "dataset": "All India Tourist Attractions (10,025)",
        "path": str(csv_path.name),
        "total_rows": 0,
        "valid_rows": 0,
        "bad_coordinates": 0,
        "missing_hours": 0,
        "non_positive_prices": 0,
        "generic_or_empty_names": 0,
        "stale_rows": 0,
        "sample_issues": []
    }

    if not csv_path.exists():
        stats["error"] = f"File not found: {csv_path}"
        return stats

    today = date.today()

    try:
        df = pd.read_csv(csv_path)
        stats["total_rows"] = len(df)

        for idx, row in df.iterrows():
            row_id = idx + 2
            issues = []
            name = str(row.get("Name", "")).strip()

            # 1. Name Check
            if not name or name.lower() in ("unknown", "unnamed", "place", "site", "none"):
                issues.append("empty_or_placeholder_name")
                stats["generic_or_empty_names"] += 1

            # 2. Coordinates Check
            try:
                lat = float(row.get("Latitude"))
                lon = float(row.get("Longitude"))
                if not (INDIA_LAT_MIN <= lat <= INDIA_LAT_MAX and INDIA_LON_MIN <= lon <= INDIA_LON_MAX):
                    issues.append(f"bad_coordinates (lat={lat}, lon={lon})")
                    stats["bad_coordinates"] += 1
            except (ValueError, TypeError):
                issues.append("invalid_or_missing_coordinates")
                stats["bad_coordinates"] += 1

            # 3. Hours Check
            try:
                hrs = float(row.get("Time Needed to Visit (hrs)"))
                if hrs <= 0 or hrs > 16.0:
                    issues.append(f"invalid_hours (hrs={hrs})")
                    stats["missing_hours"] += 1
            except (ValueError, TypeError):
                issues.append("missing_hours")
                stats["missing_hours"] += 1

            # 4. Price Check (Entrance fee can be 0 for free monuments, but not negative or NaN)
            try:
                fee = float(row.get("Entrance Fee in INR"))
                if fee < 0 or fee > 50000:
                    issues.append(f"invalid_fee (fee={fee})")
                    stats["non_positive_prices"] += 1
            except (ValueError, TypeError):
                issues.append("missing_fee")
                stats["non_positive_prices"] += 1

            # 5. Stale date check if present
            lv_str = str(row.get("last_verified", "")).strip()
            if lv_str:
                try:
                    lv_date = date.fromisoformat(lv_str)
                    if (today - lv_date).days > 730:
                        issues.append(f"stale_data ({lv_str})")
                        stats["stale_rows"] += 1
                except Exception:
                    pass

            if issues:
                if len(stats["sample_issues"]) < 5:
                    stats["sample_issues"].append({
                        "row": row_id,
                        "name": name,
                        "issues": issues
                    })
            else:
                stats["valid_rows"] += 1

    except Exception as e:
        stats["error"] = str(e)

    return stats


def validate_hotels_dataset(csv_path: Path) -> dict:
    """Validates 2_All_India_Hotels_and_Accommodations_150000.csv."""
    stats = {
        "dataset": "All India Accommodations (150,000)",
        "path": str(csv_path.name),
        "total_rows": 0,
        "valid_rows": 0,
        "non_positive_prices": 0,
        "invalid_ratings": 0,
        "invalid_safety_scores": 0,
        "empty_names_or_cities": 0,
        "stale_rows": 0,
        "sample_issues": []
    }

    if not csv_path.exists():
        stats["error"] = f"File not found: {csv_path}"
        return stats

    today = date.today()

    try:
        with open(csv_path, "r", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            for idx, row in enumerate(reader):
                stats["total_rows"] += 1
                row_id = idx + 2
                issues = []
                name = (row.get("property_name") or "").strip()
                city = (row.get("city") or "").strip()

                if not name or not city:
                    issues.append("missing_name_or_city")
                    stats["empty_names_or_cities"] += 1

                # Price check: hotels must have positive prices (> 0)
                try:
                    price = float(row.get("price_per_night_inr") or 0)
                    if price <= 0:
                        issues.append(f"non_positive_price ({price})")
                        stats["non_positive_prices"] += 1
                except (ValueError, TypeError):
                    issues.append("invalid_price_format")
                    stats["non_positive_prices"] += 1

                # Star rating check: 1.0 to 5.0
                try:
                    stars = float(row.get("star_rating") or 0)
                    if not (1.0 <= stars <= 5.0):
                        issues.append(f"invalid_star_rating ({stars})")
                        stats["invalid_ratings"] += 1
                except (ValueError, TypeError):
                    issues.append("missing_star_rating")
                    stats["invalid_ratings"] += 1

                # Safety score check: 0.0 to 10.0
                try:
                    safety = float(row.get("safety_score") or 0)
                    if not (0.0 <= safety <= 10.0):
                        issues.append(f"invalid_safety_score ({safety})")
                        stats["invalid_safety_scores"] += 1
                except (ValueError, TypeError):
                    issues.append("missing_safety_score")
                    stats["invalid_safety_scores"] += 1

                # Stale date check if present
                lv_str = (row.get("last_verified") or "").strip()
                if lv_str:
                    try:
                        lv_date = date.fromisoformat(lv_str)
                        if (today - lv_date).days > 730:
                            issues.append(f"stale_data ({lv_str})")
                            stats["stale_rows"] += 1
                    except Exception:
                        pass

                if issues:
                    if len(stats["sample_issues"]) < 5:
                        stats["sample_issues"].append({
                            "row": row_id,
                            "name": name,
                            "city": city,
                            "issues": issues
                        })
                else:
                    stats["valid_rows"] += 1

    except Exception as e:
        stats["error"] = str(e)

    return stats


def print_report(attraction_stats: dict, hotel_stats: dict):
    """Outputs structured audit report."""
    print("=" * 80)
    print("       YATRIKA DATASET INTEGRITY & STALENESS AUDIT REPORT")
    print("=" * 80)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Datasets Directory: {DATASETS_DIR}\n")

    for stats in [attraction_stats, hotel_stats]:
        print("-" * 80)
        print(f"Dataset: {stats['dataset']} [{stats.get('path', '')}]")
        print("-" * 80)
        if "error" in stats:
            print(f"  [ERROR] {stats['error']}")
            continue

        tot = stats["total_rows"]
        val = stats["valid_rows"]
        inv = tot - val
        health_pct = (val / tot * 100) if tot > 0 else 0.0

        print(f"  Total Rows:         {tot:,}")
        print(f"  Valid Rows:         {val:,} ({health_pct:.2f}%)")
        print(f"  Flagged Rows:       {inv:,} ({(100 - health_pct):.2f}%)")

        # Specific metric breakdown
        for k, v in stats.items():
            if k not in ("dataset", "path", "total_rows", "valid_rows", "sample_issues", "error"):
                print(f"    - {k.replace('_', ' ').title()}: {v:,}")

        if stats.get("sample_issues"):
            print("\n  Sample Flagged Rows:")
            for sample in stats["sample_issues"]:
                print(f"    Line {sample['row']}: '{sample.get('name', 'N/A')}' -> {', '.join(sample['issues'])}")
        print()

    print("=" * 80)
    print("Audit Complete. Dataset validation finished cleanly.")
    print("=" * 80)


def main():
    attractions_csv = DATASETS_DIR / "1_All_India_Tourist_Attractions_10025.csv"
    hotels_csv = DATASETS_DIR / "2_All_India_Hotels_and_Accommodations_150000.csv"

    attr_stats = validate_attractions_dataset(attractions_csv)
    hotel_stats = validate_hotels_dataset(hotels_csv)

    print_report(attr_stats, hotel_stats)
    return 0


if __name__ == "__main__":
    sys.exit(main())
