"""
TravelPlannerAgent - Database Initialization & Helper
"""

import sqlite3
import os
from backend.config import get_config

cfg = get_config()
DATABASE_PATH = cfg.DATABASE_PATH


def get_db_connection() -> sqlite3.Connection:
    """Return a SQLite connection with row_factory enabled."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    """Create all tables if they don't exist."""
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
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
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id             INTEGER NOT NULL,
            destination         TEXT    NOT NULL,
            start_date          TEXT    NOT NULL,
            end_date            TEXT    NOT NULL,
            num_days            INTEGER NOT NULL,
            budget              REAL    NOT NULL,
            num_travelers       INTEGER NOT NULL DEFAULT 1,
            travel_style        TEXT    DEFAULT 'budget',
            transport           TEXT    DEFAULT 'flight',
            interests           TEXT    DEFAULT '',
            special_requirements TEXT   DEFAULT '',
            itinerary_json      TEXT    DEFAULT NULL,
            weather_json        TEXT    DEFAULT NULL,
            budget_json         TEXT    DEFAULT NULL,
            hotels_json         TEXT    DEFAULT NULL,
            status              TEXT    DEFAULT 'draft',
            created_at          TEXT    DEFAULT (datetime('now')),
            updated_at          TEXT    DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

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
