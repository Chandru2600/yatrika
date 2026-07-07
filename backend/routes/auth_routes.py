"""
TravelPlannerAgent - Authentication Routes (Blueprint)
"""

from flask import (
    Blueprint, request, render_template, redirect,
    url_for, session, flash, jsonify
)
from functools import wraps
from backend.models.user import (
    create_user, get_user_by_email, verify_password,
    update_last_login, get_user_by_id
)

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


# ── Decorators ────────────────────────────────────────────────

def login_required(f):
    """Redirect to login if session is not authenticated."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("Please login to continue.", "warning")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    """Redirect unless the logged-in user has admin role."""
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_user_by_id(session.get("user_id"))
        if not user or user["role"] != "admin":
            flash("Admin access required.", "danger")
            return redirect(url_for("main.dashboard"))
        return f(*args, **kwargs)
    return decorated


# ── Routes ────────────────────────────────────────────────────

@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    """User registration."""
    if "user_id" in session:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        name     = request.form.get("name", "").strip()
        email    = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm  = request.form.get("confirm_password", "")

        # Validations
        if not name or not email or not password:
            flash("All fields are required.", "danger")
            return render_template("auth/register.html")

        if len(password) < 8:
            flash("Password must be at least 8 characters.", "danger")
            return render_template("auth/register.html")

        if password != confirm:
            flash("Passwords do not match.", "danger")
            return render_template("auth/register.html")

        if get_user_by_email(email):
            flash("Email already registered. Please login.", "warning")
            return redirect(url_for("auth.login"))

        try:
            user_id = create_user(name, email, password)
            session.permanent = True
            session["user_id"]   = user_id
            session["user_name"] = name
            session["user_role"] = "user"
            flash(f"Welcome, {name}! Your account has been created.", "success")
            return redirect(url_for("main.dashboard"))
        except Exception as e:
            flash(f"Registration failed: {e}", "danger")
            return render_template("auth/register.html")

    return render_template("auth/register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """User login."""
    if "user_id" in session:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        email    = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = get_user_by_email(email)
        if user and verify_password(password, user["password"]):
            session.permanent = True
            session["user_id"]   = user["id"]
            session["user_name"] = user["name"]
            session["user_role"] = user["role"]
            update_last_login(user["id"])
            flash(f"Welcome back, {user['name']}!", "success")
            next_page = request.args.get("next", url_for("main.dashboard"))
            return redirect(next_page)
        else:
            flash("Invalid email or password.", "danger")

    return render_template("auth/login.html")


@auth_bp.route("/logout")
def logout():
    """Clear session and redirect to home."""
    name = session.get("user_name", "User")
    session.clear()
    flash(f"Goodbye, {name}! You have been logged out.", "info")
    return redirect(url_for("main.home"))


@auth_bp.route("/profile", methods=["GET"])
@login_required
def profile():
    """User profile page."""
    user = get_user_by_id(session["user_id"])
    return render_template("auth/profile.html", user=user)
