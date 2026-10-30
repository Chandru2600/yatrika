"""
TravelPlannerAgent - Database Initialization & Helper
"""

import sqlite3
import os
import secrets
from backend.config import get_config

cfg = get_config()
DATABASE_PATH = os.environ.get("DATABASE_PATH") or cfg.DATABASE_PATH


def get_database_path() -> str:
    """Return active database path from Flask config or default."""
    from flask import current_app, has_app_context
    if has_app_context():
        return current_app.config.get("DATABASE_PATH") or os.environ.get("DATABASE_PATH") or DATABASE_PATH
    return os.environ.get("DATABASE_PATH") or DATABASE_PATH


def get_db_connection() -> sqlite3.Connection:
    """Return a SQLite connection with row_factory enabled."""
    db_path = get_database_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    """Create all tables if they don't exist."""
    db_path = get_database_path()
    if db_path != ":memory:":
        db_dir = os.path.dirname(db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
    conn = get_db_connection()
    cursor = conn.cursor()

    # ── Users ─────────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT    NOT NULL,
            email       TEXT    NOT NULL UNIQUE,
            password    TEXT    NOT NULL,
            role        TEXT    NOT NULL DEFAULT 'user',
            avatar      TEXT    DEFAULT NULL,
            created_at  TEXT    DEFAULT (datetime('now')),
            last_login  TEXT    DEFAULT NULL
        )
    """)

    # ── Trips ─────────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trips (
            id                   INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id              INTEGER NOT NULL,
            destination          TEXT    NOT NULL,
            start_date           TEXT    NOT NULL,
            end_date             TEXT    NOT NULL,
            num_days             INTEGER NOT NULL,
            budget               REAL    NOT NULL,
            num_travelers        INTEGER NOT NULL DEFAULT 1,
            travel_style         TEXT    DEFAULT 'budget',
            transport            TEXT    DEFAULT 'flight',
            transit_mode         TEXT    DEFAULT 'car',
            transit_cost         REAL    DEFAULT 0,
            arrival_time         TEXT    DEFAULT '10:00',
            transit_details_json TEXT    DEFAULT NULL,
            interests            TEXT    DEFAULT '',
            special_requirements TEXT   DEFAULT '',
            itinerary_json       TEXT    DEFAULT NULL,
            weather_json         TEXT    DEFAULT NULL,
            budget_json          TEXT    DEFAULT NULL,
            hotels_json          TEXT    DEFAULT NULL,
            checklist_json       TEXT    DEFAULT NULL,
            status               TEXT    DEFAULT 'draft',
            created_at           TEXT    DEFAULT (datetime('now')),
            updated_at           TEXT    DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    # Check and apply migrations for existing DBs
    cursor.execute("PRAGMA table_info(trips)")
    cols = [column[1] for column in cursor.fetchall()]
    if "transit_mode" not in cols:
        cursor.execute("ALTER TABLE trips ADD COLUMN transit_mode TEXT DEFAULT 'car'")
    if "transit_cost" not in cols:
        cursor.execute("ALTER TABLE trips ADD COLUMN transit_cost REAL DEFAULT 0")
    if "arrival_time" not in cols:
        cursor.execute("ALTER TABLE trips ADD COLUMN arrival_time TEXT DEFAULT '10:00'")
    if "transit_details_json" not in cols:
        cursor.execute("ALTER TABLE trips ADD COLUMN transit_details_json TEXT DEFAULT NULL")
    if "share_token" not in cols:
        cursor.execute("ALTER TABLE trips ADD COLUMN share_token TEXT DEFAULT NULL")
    if "is_public" not in cols:
        cursor.execute("ALTER TABLE trips ADD COLUMN is_public INTEGER DEFAULT 0")
    if "checklist_json" not in cols:
        cursor.execute("ALTER TABLE trips ADD COLUMN checklist_json TEXT DEFAULT NULL")
    cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_trips_share_token ON trips(share_token) WHERE share_token IS NOT NULL")

    # Securely backfill missing share tokens for any existing trips (defaulting to private is_public=0)
    cursor.execute("SELECT id FROM trips WHERE share_token IS NULL")
    for row in cursor.fetchall():
        cursor.execute("UPDATE trips SET share_token = ?, is_public = 0 WHERE id = ?", (secrets.token_urlsafe(16), row[0]))


    # ── SavedTrips ────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS saved_trips (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER NOT NULL,
            trip_id    INTEGER NOT NULL,
            saved_at   TEXT    DEFAULT (datetime('now')),
            notes      TEXT    DEFAULT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (trip_id) REFERENCES trips(id) ON DELETE CASCADE
        )
    """)

    # ── TravelHistory ─────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS travel_history (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id      INTEGER NOT NULL,
            trip_id      INTEGER NOT NULL,
            visited_at   TEXT    DEFAULT (datetime('now')),
            rating       INTEGER DEFAULT NULL,
            review       TEXT    DEFAULT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (trip_id) REFERENCES trips(id) ON DELETE CASCADE
        )
    """)

    # ── Expenses ──────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            trip_id     INTEGER NOT NULL,
            category    TEXT    NOT NULL,
            amount      REAL    NOT NULL,
            description TEXT    DEFAULT NULL,
            date        TEXT    DEFAULT (datetime('now')),
            FOREIGN KEY (trip_id) REFERENCES trips(id) ON DELETE CASCADE
        )
    """)

    # ── OSRM Route Cache ──────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS osrm_cache (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            cache_key     TEXT    NOT NULL UNIQUE,
            response_json TEXT    NOT NULL,
            created_at    TEXT    DEFAULT (datetime('now'))
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_osrm_cache_key ON osrm_cache(cache_key)")

    conn.commit()
    conn.close()
    print("[DB] Tables initialized successfully.")


def execute_query(query: str, params: tuple = (), fetchone: bool = False):
    """Generic query executor."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(query, params)
    if fetchone:
        result = cursor.fetchone()
    else:
        result = cursor.fetchall()
    conn.commit()
    conn.close()
    return result


def execute_insert(query: str, params: tuple = ()) -> int:
    """Execute an INSERT and return lastrowid."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(query, params)
    row_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return row_id
