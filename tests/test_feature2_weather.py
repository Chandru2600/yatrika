"""
Feature 2 Tests - Real Weather Forecast for Travel Dates & Dynamic Alerts
Verifies:
1. Open-Meteo forecast API integration without API key.
2. Rain and Extreme Heat detection with badge and swap recommendations.
3. In-memory caching per (lat, lon, date).
4. Zero-crash graceful degradation when offline or network fails.
5. Full attachment of weather alerts to itinerary days.
"""

import unittest
from unittest.mock import patch, MagicMock
from backend.services.weather.weather_service import (
    fetch_open_meteo_forecast,
    get_cached_weather,
    set_cached_weather,
    attach_weather_forecast_to_itinerary,
    _open_meteo_cache
)


class Feature2WeatherTestCase(unittest.TestCase):
    def setUp(self):
        # Clear cache before each test
        _open_meteo_cache.clear()

    def test_cache_set_and_get(self):
        lat, lon = 12.424, 75.738
        date_str = "2026-10-15"
        data = {"temp_max": 28.5, "condition": "Sunny"}

        self.assertIsNone(get_cached_weather(lat, lon, date_str))
        set_cached_weather(lat, lon, date_str, data)
        cached = get_cached_weather(lat, lon, date_str)
        self.assertIsNotNone(cached)
        self.assertEqual(cached["temp_max"], 28.5)

    def test_fetch_open_meteo_forecast_uses_cache(self):
        lat, lon = 15.299, 74.124
        date_str = "2026-10-20"
        mock_alert = {
            "has_alert": True,
            "type": "rain",
            "badge": "🌧️ Rain Forecast",
            "suggestion": "Move outdoor viewpoint visits to morning slots."
        }
        set_cached_weather(lat, lon, date_str, mock_alert)

        # Should fetch from cache without calling requests.get
        with patch("requests.get") as mock_get:
            res = fetch_open_meteo_forecast(lat, lon, [date_str])
            mock_get.assert_not_called()
            self.assertIn(date_str, res)
            self.assertEqual(res[date_str]["badge"], "🌧️ Rain Forecast")

    def test_rain_alert_detection(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "daily": {
                "time": ["2026-10-25"],
                "temperature_2m_max": [27.0],
                "temperature_2m_min": [21.0],
                "precipitation_sum": [15.2],
                "precipitation_probability_max": [85],
                "weathercode": [63]  # Rain (moderate)
            }
        }

        with patch("requests.get", return_value=mock_response):
            res = fetch_open_meteo_forecast(12.42, 75.74, ["2026-10-25"])
            self.assertIn("2026-10-25", res)
            day_w = res["2026-10-25"]
            self.assertTrue(day_w["has_alert"])
            self.assertEqual(day_w["type"], "rain")
            self.assertIn("Rain Forecast", day_w["badge"])
            self.assertIn("indoor", day_w["suggestion"].lower())

    def test_extreme_heat_alert_detection(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "daily": {
                "time": ["2026-05-15"],
                "temperature_2m_max": [41.5],
                "temperature_2m_min": [29.0],
                "precipitation_sum": [0.0],
                "precipitation_probability_max": [5],
                "weathercode": [0]
            }
        }

        with patch("requests.get", return_value=mock_response):
            res = fetch_open_meteo_forecast(26.91, 75.78, ["2026-05-15"])
            self.assertIn("2026-05-15", res)
            day_w = res["2026-05-15"]
            self.assertTrue(day_w["has_alert"])
            self.assertEqual(day_w["type"], "heat")
            self.assertIn("Heat Alert", day_w["badge"])
            self.assertIn("morning hours", day_w["suggestion"].lower())

    def test_attach_weather_forecast_to_itinerary_offline_graceful(self):
        itinerary = {
            "days": [
                {"day": 1, "date": "2026-11-01", "morning": {"name": "Fort"}},
                {"day": 2, "date": "2026-11-02", "morning": {"name": "Palace"}}
            ]
        }

        # Simulate complete offline / network error
        with patch("requests.get", side_effect=Exception("Network unreachable")):
            enriched = attach_weather_forecast_to_itinerary(itinerary, "Coorg", "2026-11-01")
            self.assertIsInstance(enriched, dict)
            self.assertEqual(len(enriched["days"]), 2)
            # Days remain intact with no crash; weather_alert is safely None
            self.assertIsNone(enriched["days"][0].get("weather_alert"))
            self.assertIsNone(enriched["days"][1].get("weather_alert"))

    def test_attach_weather_forecast_with_rain_alert(self):
        itinerary = {
            "days": [
                {"day": 1, "date": "2026-11-01", "morning": {"name": "Waterfalls"}},
                {"day": 2, "date": "2026-11-02", "morning": {"name": "Peak Viewpoint"}}
            ]
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "daily": {
                "time": ["2026-11-01", "2026-11-02"],
                "temperature_2m_max": [26.0, 28.0],
                "temperature_2m_min": [19.0, 20.0],
                "precipitation_sum": [18.0, 0.0],
                "precipitation_probability_max": [80, 10],
                "weathercode": [61, 1]
            }
        }

        with patch("requests.get", return_value=mock_response):
            enriched = attach_weather_forecast_to_itinerary(itinerary, "Coorg", "2026-11-01")
            day1 = enriched["days"][0]
            self.assertIsNotNone(day1.get("weather_alert"))
            self.assertTrue(day1["weather_alert"]["has_alert"])
            self.assertEqual(day1["weather_alert"]["type"], "rain")

            day2 = enriched["days"][1]
            self.assertIsNotNone(day2.get("weather_alert"))
            self.assertFalse(day2["weather_alert"]["has_alert"])
