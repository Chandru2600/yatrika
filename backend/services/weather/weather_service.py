"""
TravelPlannerAgent - Weather Service (OpenWeatherMap)
"""

import requests
from backend.config import get_config

def get_current_weather(city: str) -> dict:
    """
    Fetch current weather for a city using OpenWeatherMap.

    Returns a normalized dict with temperature, humidity,
    wind, sunrise, sunset, and description.
    """
    try:
        cfg = get_config()
        url = f"{cfg.WEATHER_BASE_URL}/weather"
        params = {
            "q":     city,
            "appid": cfg.WEATHER_API_KEY,
            "units": "metric"
        }
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        return {
            "city":        data["name"],
            "country":     data["sys"]["country"],
            "temperature": round(data["main"]["temp"], 1),
            "feels_like":  round(data["main"]["feels_like"], 1),
            "humidity":    data["main"]["humidity"],
            "wind_speed":  data["wind"]["speed"],
            "description": data["weather"][0]["description"].title(),
            "icon":        data["weather"][0]["icon"],
            "sunrise":     data["sys"]["sunrise"],
            "sunset":      data["sys"]["sunset"],
            "visibility":  data.get("visibility", 0) // 1000,   # km
            "pressure":    data["main"]["pressure"],
            "error":       None
        }
    except requests.HTTPError as e:
        return {"error": f"Weather API error: {e.response.status_code}", "city": city}
    except Exception as e:
        return {"error": str(e), "city": city}


def get_forecast(city: str, days: int = 7) -> dict:
    """
    Fetch a 5-day (40 × 3-hour intervals) forecast and
    aggregate it into daily summaries.
    """
    try:
        cfg = get_config()
        url = f"{cfg.WEATHER_BASE_URL}/forecast"
        params = {
            "q":     city,
            "appid": cfg.WEATHER_API_KEY,
            "units": "metric",
            "cnt":   40                # 5 days × 8 intervals
        }
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        # Aggregate: group by date, pick midday entry
        daily: dict = {}
        for item in data["list"]:
            date = item["dt_txt"][:10]
            if date not in daily:
                daily[date] = {
                    "date":        date,
                    "temp_min":    item["main"]["temp_min"],
                    "temp_max":    item["main"]["temp_max"],
                    "description": item["weather"][0]["description"].title(),
                    "icon":        item["weather"][0]["icon"],
                    "humidity":    item["main"]["humidity"],
                    "rain_prob":   round(item.get("pop", 0) * 100)
                }
            else:
                daily[date]["temp_min"] = min(daily[date]["temp_min"], item["main"]["temp_min"])
                daily[date]["temp_max"] = max(daily[date]["temp_max"], item["main"]["temp_max"])

        forecast_list = list(daily.values())[:days]
        return {"city": city, "forecast": forecast_list, "error": None}
    except requests.HTTPError as e:
        return {"error": f"Forecast API error: {e.response.status_code}"}
    except Exception as e:
        return {"error": str(e)}


def get_travel_weather_advice(weather: dict) -> list:
    """
    Return human-readable travel alerts based on weather data.
    """
    alerts = []
    if not weather or weather.get("error"):
        return ["Weather data unavailable. Check local forecasts."]

    temp = weather.get("temperature", 20)
    humidity = weather.get("humidity", 50)
    wind = weather.get("wind_speed", 0)
    desc = weather.get("description", "").lower()

    if temp > 38:
        alerts.append("⚠️ Extreme heat! Carry water, use sunscreen, avoid midday outdoors.")
    elif temp > 30:
        alerts.append("☀️ Hot weather expected. Light clothing and hydration recommended.")
    elif temp < 5:
        alerts.append("🥶 Very cold! Pack heavy winter clothing and thermal wear.")
    elif temp < 15:
        alerts.append("🧥 Cool weather. Pack a jacket and layered clothing.")

    if humidity > 80:
        alerts.append("💧 High humidity. Breathable fabrics strongly recommended.")

    if wind > 10:
        alerts.append("💨 Strong winds expected. Secure loose items and accessories.")

    if "rain" in desc or "drizzle" in desc:
        alerts.append("🌧️ Rain expected. Carry an umbrella and waterproof footwear.")
    if "storm" in desc or "thunderstorm" in desc:
        alerts.append("⛈️ Thunderstorms possible. Avoid open areas and stay indoors.")
    if "snow" in desc:
        alerts.append("❄️ Snowfall expected. Anti-slip footwear and warm layers essential.")
    if "fog" in desc or "mist" in desc:
        alerts.append("🌫️ Foggy conditions. Reduced visibility—drive carefully.")

    if not alerts:
        alerts.append("✅ Weather looks great for travel! Enjoy your trip.")

    return alerts
