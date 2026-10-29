"""
TravelPlannerAgent - User Model
"""

import bcrypt
import hashlib
import os
from backend.database.db import execute_query, execute_insert


def hash_password(password: str) -> str:
    """Hash password using bcrypt with random salt."""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(password: str, stored: str) -> bool:
    """
    Verify password against stored hash.
    Supports bcrypt ($2b$, $2a$, $2y$) as well as legacy SHA-256 (salt:hash)
    for seamless backward compatibility.
    """
    if not stored:
        return False
    # Legacy SHA-256 format: salt:hash
    if ":" in stored and not stored.startswith("$2"):
        try:
            salt, hashed = stored.split(":", 1)
            return hashlib.sha256((password + salt).encode("utf-8")).hexdigest() == hashed
        except Exception:
            return False
    try:
        return bcrypt.checkpw(password.encode("utf-8"), stored.encode("utf-8"))
    except Exception:
        return False


def create_user(name: str, email: str, password: str, role: str = "user") -> int:
    """Insert a new user and return the new user ID."""
    hashed_pw = hash_password(password)
    return execute_insert(
        "INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)",
        (name, email, hashed_pw, role)
    )


def get_user_by_email(email: str):
    """Fetch a user row by email."""
    return execute_query(
        "SELECT * FROM users WHERE email = ?",
        (email,),
        fetchone=True
    )


def get_user_by_id(user_id: int):
    """Fetch a user row by ID."""
    return execute_query(
        "SELECT * FROM users WHERE id = ?",
        (user_id,),
        fetchone=True
    )


def update_last_login(user_id: int) -> None:
    """Stamp last_login for the given user."""
    execute_query(
        "UPDATE users SET last_login = datetime('now') WHERE id = ?",
        (user_id,)
    )


def get_all_users():
    """Return all users (admin use)."""
    return execute_query(
        "SELECT id, name, email, role, created_at, last_login FROM users ORDER BY created_at DESC"
    )


def update_user_profile(user_id: int, name: str, avatar: str = None) -> None:
    """Update user name/avatar."""
    execute_query(
        "UPDATE users SET name = ?, avatar = ? WHERE id = ?",
        (name, avatar, user_id)
    )


def delete_user(user_id: int) -> None:
    """Delete user and cascade trips."""
    execute_query("DELETE FROM users WHERE id = ?", (user_id,))


def count_users() -> int:
    """Return total user count."""
    row = execute_query("SELECT COUNT(*) as cnt FROM users", fetchone=True)
    return row["cnt"] if row else 0


def create_isolated_guest_user() -> int:
    """Create a unique, isolated guest traveler account for an anonymous visitor."""
    import secrets
    guest_token = secrets.token_hex(6)
    name = f"Guest Traveler {guest_token.upper()}"
    email = f"guest_{guest_token}@guest.yatrika.local"
    pw = secrets.token_urlsafe(16)
    return create_user(name, email, pw, role="guest")


def migrate_guest_trips_to_user(guest_user_id: int, target_user_id: int) -> int:
    """Transfer trips and saved_trips created during an anonymous session to a newly registered user."""
    if not guest_user_id or not target_user_id or guest_user_id == target_user_id:
        return 0
    execute_query("UPDATE trips SET user_id = ? WHERE user_id = ?", (target_user_id, guest_user_id))
    execute_query("UPDATE saved_trips SET user_id = ? WHERE user_id = ?", (target_user_id, guest_user_id))
    return 1
