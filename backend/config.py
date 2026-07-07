"""
TravelPlannerAgent - Configuration Module
"""

import os
from datetime import timedelta

class Config:
    """Base configuration class."""

    # ── Flask ────────────────────────────────────────────────
    SECRET_KEY = os.environ.get("SECRET_KEY", "ibm-travel-planner-secret-2024")
    DEBUG = False
    TESTING = False

    # ── Session ──────────────────────────────────────────────
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_HTTPONLY = True

    # ── Database ─────────────────────────────────────────────
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DATABASE_PATH = os.path.join(BASE_DIR, "database", "travel_planner.db")

    # ── IBM watsonx.ai / Granite ──────────────────────────────
    # Read at access time so .env changes take effect without restart
    IBM_API_KEY      = ""
    IBM_PROJECT_ID   = ""
    IBM_WATSONX_URL  = "https://us-south.ml.cloud.ibm.com"
    GRANITE_MODEL_ID = "ibm/granite-4-h-small"

    # ── OpenWeatherMap ────────────────────────────────────────
    WEATHER_API_KEY  = ""
    WEATHER_BASE_URL = "https://api.openweathermap.org/data/2.5"

    # ── Currency Exchange ─────────────────────────────────────
    EXCHANGE_API_KEY  = ""
    EXCHANGE_BASE_URL = "https://v6.exchangerate-api.com/v6"

    def __init__(self):
        """Read all env vars at instantiation time (after load_dotenv)."""
        self.IBM_API_KEY      = os.environ.get("IBM_API_KEY", "").strip()
        self.IBM_PROJECT_ID   = (os.environ.get("IBM_PROJECT_ID") or os.environ.get("WATSONX_PROJECT_ID", "")).strip()
        self.IBM_WATSONX_URL  = (os.environ.get("IBM_WATSONX_URL") or os.environ.get("WATSONX_URL", "https://us-south.ml.cloud.ibm.com")).strip()
        self.GRANITE_MODEL_ID = os.environ.get("GRANITE_MODEL_ID", "ibm/granite-4-h-small").strip()
        self.WEATHER_API_KEY  = (os.environ.get("WEATHER_API_KEY") or os.environ.get("OPENWEATHER_API_KEY", "")).strip()
        self.EXCHANGE_API_KEY = os.environ.get("EXCHANGE_API_KEY", "").strip()

    # ── Upload ────────────────────────────────────────────────
    UPLOAD_FOLDER      = os.path.join(BASE_DIR, "uploads")
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024   # 16 MB

    # ── PDF ───────────────────────────────────────────────────
    PDF_OUTPUT_FOLDER  = os.path.join(BASE_DIR, "pdf_reports")


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    SESSION_COOKIE_SECURE = False


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    SESSION_COOKIE_SECURE = True


class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    DATABASE_PATH = ":memory:"


# ── Active config ─────────────────────────────────────────────
config_map = {
    "development": DevelopmentConfig,
    "production":  ProductionConfig,
    "testing":     TestingConfig,
}

def get_config(env: str = "development") -> Config:
    cls = config_map.get(env, DevelopmentConfig)
    return cls()
