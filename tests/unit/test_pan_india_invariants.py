"""Pan-India invariant tests across diverse Indian cities, modes, and budgets."""

import pytest
from backend.agents_models.cooperative_pipeline import MultiAgentCooperativePipeline
from backend.services.weather.weather_service import get_forecast


@pytest.mark.parametrize(
    "source,dest,mode,days,trav,budget",
    [
        ("Bengaluru", "Coorg", "bus", 3, 2, 30000),
        ("Bengaluru", "Mysuru", "train", 2, 2, 15000),
        ("Bengaluru", "Shimla", "flight", 4, 2, 30000),
        ("Bengaluru", "Varanasi", "train", 4, 2, 30000),
        ("Bengaluru", "Agra", "bus", 4, 2, 30000),
        ("Mangaluru", "Hampi", "car", 4, 3, 50000),
    ],
)
def test_pan_india_pipeline_invariants(source, dest, mode, days, trav, budget):
    pipe = MultiAgentCooperativePipeline()
    plan = pipe.run_pipeline({
        "source": source,
        "destination": dest,
        "num_days": days,
        "num_travelers": trav,
        "budget": budget,
        "travel_style": "balanced",
        "transport": mode,
    })
    assert plan and "itinerary" in plan
    b = plan["budget"]
    breakdown = b.get("breakdown", {})
    assert breakdown, "Missing budget breakdown"
    sum_breakdown = sum(float(v.get("amount", 0) or 0) for v in breakdown.values())
    assert abs(sum_breakdown - float(b["committed_total_inr"])) <= 5.0
    for cat, info in breakdown.items():
        assert 0.0 <= float(info.get("percentage", 0)) <= 500.0  # bounded ratio when over target
        assert float(info.get("amount", 0)) >= 0.0

    tl = plan["itinerary"]["timeline"]
    assert tl["source"].lower() == source.lower()
    events = [ev["title"] for d in tl["days"] for ev in d["events"]]
    assert any("Return to" in t for t in events)


def test_open_meteo_daily_minmax_forecast():
    fc = get_forecast("Agra", days=4)
    assert fc.get("forecast")
    day0 = fc["forecast"][0]
    assert "temp_min" in day0 and "temp_max" in day0
    assert day0["temp_max"] >= day0["temp_min"]
