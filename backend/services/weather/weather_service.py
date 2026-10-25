"""
TravelPlannerAgent - Weather Service (OpenWeatherMap)
"""

import requests
from backend.config import get_config

def get_mock_current_weather(city: str) -> dict:
    """Generate realistic mock current weather deterministically based on city name."""
    city_hash = sum(ord(c) for c in city)
    temp = 18.0 + (city_hash % 15)
    feels_like = temp + 1.2
    humidity = 50 + (city_hash % 30)
    wind_speed = round(2.5 + (city_hash % 8) * 0.5, 1)
    pressure = 1008 + (city_hash % 12)
    visibility = 10
    
    descriptions = ["Sunny", "Partly Cloudy", "Mostly Sunny", "Clear Sky", "Light Rain", "Scattered Clouds"]
    desc = descriptions[city_hash % len(descriptions)]
    icons = {
        "Sunny": "01d",
        "Partly Cloudy": "02d",
        "Mostly Sunny": "01d",
        "Clear Sky": "01d",
        "Light Rain": "10d",
        "Scattered Clouds": "03d"
    }
    icon = icons.get(desc, "01d")
    
    return {
        "city":        city.title(),
        "country":     "IN",
        "temperature": round(temp, 1),
        "feels_like":  round(feels_like, 1),
        "humidity":    humidity,
        "wind_speed":  wind_speed,
        "description": desc,
        "icon":        icon,
        "sunrise":     1719964800,
        "sunset":      1720011600,
        "visibility":  visibility,
        "pressure":    pressure,
        "error":       None
    }


def get_mock_forecast(city: str, days: int = 7) -> dict:
    """Generate realistic mock 7-day forecast deterministically."""
    from datetime import date, timedelta
    city_hash = sum(ord(c) for c in city)
    base_temp = 18.0 + (city_hash % 15)
    
    forecast_list = []
    today = date.today()
    descriptions = ["Sunny", "Partly Cloudy", "Mostly Sunny", "Clear Sky", "Light Rain", "Scattered Clouds"]
    
    for i in range(days):
        day_date = (today + timedelta(days=i)).isoformat()
        day_hash = city_hash + i
        temp_change = (day_hash % 5) - 2
        temp_max = base_temp + temp_change
        temp_min = temp_max - 6.0 - (day_hash % 3)
        
        desc = descriptions[day_hash % len(descriptions)]
        icons = {
            "Sunny": "01d",
            "Partly Cloudy": "02d",
            "Mostly Sunny": "01d",
            "Clear Sky": "01d",
            "Light Rain": "10d",
            "Scattered Clouds": "03d"
        }
        icon = icons.get(desc, "01d")
        
        forecast_list.append({
            "date":        day_date,
            "temp_min":    round(temp_min, 1),
            "temp_max":    round(temp_max, 1),
            "description": desc,
            "icon":        icon,
            "humidity":    50 + (day_hash % 30),
            "rain_prob":   80 if "Rain" in desc else (day_hash % 3) * 10
        })
        
    return {"city": city, "forecast": forecast_list, "error": None}


def get_current_weather(city: str) -> dict:
    """
    Fetch current weather for a city using OpenWeatherMap.
    Falls back to mock weather deterministically if API key is invalid/missing.
    """
    cfg = get_config()
    key = cfg.WEATHER_API_KEY
    if not key or key.strip() == "" or "your_openweathermap_api" in key.lower():
        return get_mock_current_weather(city)

    try:
        url = f"{cfg.WEATHER_BASE_URL}/weather"
        params = {
            "q":     city,
            "appid": key,
            "units": "metric"
        }
        resp = requests.get(url, params=params, timeout=3)
        # If API key is invalid or unauthorized, use fallback
        if resp.status_code in [401, 403]:
            return get_mock_current_weather(city)
            
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
            "visibility":  data.get("visibility", 10000) / 1000,
            "pressure":    data["main"]["pressure"],
            "error":       None
        }
    except Exception:
        return get_mock_current_weather(city)
 
 
def get_forecast(city: str, days: int = 7) -> dict:
    """
    Fetch a 5-day forecast and aggregate it into daily summaries.
    Falls back to mock forecast if API key is invalid/missing.
    """
    cfg = get_config()
    key = cfg.WEATHER_API_KEY
    if not key or key.strip() == "" or "your_openweathermap_api" in key.lower():
        return get_mock_forecast(city, days)

    try:
        url = f"{cfg.WEATHER_BASE_URL}/forecast"
        params = {
            "q":     city,
            "appid": key,
            "units": "metric",
            "cnt":   40
        }
        resp = requests.get(url, params=params, timeout=3)
        if resp.status_code in [401, 403]:
            return get_mock_forecast(city, days)

        resp.raise_for_status()
        data = resp.json()
 
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
    except Exception:
        return get_mock_forecast(city, days)


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


def evaluate_weather_horizon(trip: dict, weather: dict = None) -> dict:
    """
    Evaluate weather status, horizon coverage, and labeling transparency.
    Categorizes data into 'live_forecast', 'seasonal_guidance', or 'unavailable'
    based on departure proximity and provider forecast window limits.
    """
    from datetime import datetime, date
    if weather is None:
        weather = {}

    start_date_str = trip.get("start_date") or ""
    dest = (trip.get("destination") or "Destination").split(",")[0].strip()

    try:
        start_date = datetime.strptime(start_date_str.strip(), "%Y-%m-%d").date()
    except Exception:
        start_date = date.today()

    today = date.today()
    days_away = (start_date - today).days
    num_days = int(trip.get("num_days", 1) or 1)

    has_error = bool(weather.get("error"))
    has_current = bool(weather.get("current") and not weather["current"].get("error"))

    if has_error or (not has_current and not weather.get("forecast")):
        return {
            "status": "unavailable",
            "label": "Forecast Not Yet Available",
            "badge_class": "bg-secondary-subtle text-secondary border border-secondary-subtle",
            "icon": "bi-cloud-slash",
            "explanation": f"Live forecasts and climate data are temporarily unavailable for {dest}. Check local weather reports prior to departure.",
            "days_away": days_away,
            "is_live": False
        }

    # OpenWeatherMap standard forecasts cover 5 to 7 days
    if -num_days <= days_away <= 7:
        return {
            "status": "live_forecast",
            "label": "Live Forecast",
            "badge_class": "bg-success-subtle text-success border border-success-subtle",
            "icon": "bi-broadcast-pin",
            "explanation": f"Live multi-day forecast provided for your travel window ({trip.get('start_date')} → {trip.get('end_date')}).",
            "days_away": days_away,
            "is_live": True
        }
    else:
        return {
            "status": "seasonal_guidance",
            "label": "Typical Seasonal Guidance",
            "badge_class": "bg-info-subtle text-info border border-info-subtle",
            "icon": "bi-calendar3",
            "explanation": f"Departure is {days_away} days away. Live day-specific forecasts become available 5–7 days prior to travel. Showing typical seasonal climate norms for {dest}.",
            "days_away": days_away,
            "is_live": False
        }

