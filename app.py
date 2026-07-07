"""
TravelPlannerAgent - Flask Application Factory
Entry point for the Flask web application.
Run with:  python app.py
"""

import os
from dotenv import load_dotenv
load_dotenv()                          # Load .env before anything else reads os.environ

from flask import Flask
from backend.config import get_config
from backend.database.db import init_db


def create_app(env: str = "development") -> Flask:
    """
    Application factory pattern.
    Creates and configures the Flask app instance.
    """
    cfg = get_config(env)

    # ── Flask instance ──────────────────────────────────────
    app = Flask(
        __name__,
        template_folder=os.path.join("frontend", "templates"),
        static_folder=os.path.join("frontend", "static")
    )
    app.config.from_object(cfg)
    app.secret_key = cfg.SECRET_KEY

    # ── Ensure upload / pdf dirs exist ──────────────────────
    os.makedirs(cfg.UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(cfg.PDF_OUTPUT_FOLDER, exist_ok=True)

    # ── Initialize database ──────────────────────────────────
    with app.app_context():
        init_db()

    # ── Register Blueprints ──────────────────────────────────
    from backend.routes.auth_routes    import auth_bp
    from backend.routes.main_routes    import main_bp
    from backend.routes.planner_routes import planner_bp
    from backend.routes.admin_routes   import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(planner_bp)
    app.register_blueprint(admin_bp)

    # ── CORS Middleware ──────────────────────────────────────
    from flask import request
    @app.after_request
    def handle_cors(response):
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization"
        response.headers["Access-Control-Allow-Methods"] = "GET,POST,PUT,DELETE,OPTIONS"
        return response

    @app.before_request
    def handle_preflight():
        if request.method == "OPTIONS":
            response = app.make_default_options_response()
            response.headers["Access-Control-Allow-Origin"] = "*"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization"
            response.headers["Access-Control-Allow-Methods"] = "GET,POST,PUT,DELETE,OPTIONS"
            return response

    # ── Jinja2 Globals ──────────────────────────────────────
    import json as _json
    app.jinja_env.globals["json_loads"] = _json.loads

    # ── Context processors ──────────────────────────────────
    @app.context_processor
    def inject_globals():
        from flask import session
        return {
            "app_name":    "AI Travel Planner",
            "app_version": "1.0.0",
            "user_name":   session.get("user_name"),
            "user_role":   session.get("user_role"),
            "user_id":     session.get("user_id"),
        }

    # ── Error handlers ──────────────────────────────────────
    @app.errorhandler(404)
    def not_found(e):
        from flask import render_template
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def server_error(e):
        from flask import render_template
        return render_template("errors/500.html"), 500

    return app


# ── Run ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    env = os.environ.get("FLASK_ENV", "development")
    application = create_app(env)
    application.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=(env == "development")
    )
