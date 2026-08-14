"""
CaribTech Labs - Application entry point.

Run locally with:
    python app.py

This uses the Flask application factory pattern so the app can be
imported cleanly by tests, WSGI servers, or the CLI without side effects.
"""

import os
import click
from flask import Flask, render_template

from config import Config
from database.extensions import db, login_manager, limiter


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # --- Init extensions ---
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please log in to access the admin dashboard."
    login_manager.login_message_category = "info"
    limiter.init_app(app)

    # Ensure upload + database directories exist
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(os.path.join(app.root_path, "database"), exist_ok=True)

    from models import Admin

    @login_manager.user_loader
    def load_user(user_id):
        return Admin.query.get(int(user_id))

    # --- Register blueprints ---
    from routes.public import public_bp
    from routes.auth import auth_bp
    from routes.admin import admin_bp

    app.register_blueprint(public_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)

    from datetime import datetime as _dt

    @app.context_processor
    def inject_globals():
        return {"current_year": _dt.utcnow().year}

    # --- Error handlers ---
    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("errors/403.html"), 403

    @app.errorhandler(401)
    def unauthorized(e):
        return render_template("errors/403.html"), 401

    @app.errorhandler(500)
    def server_error(e):
        return render_template("errors/500.html"), 500

    @app.errorhandler(413)
    def too_large(e):
        return render_template("errors/413.html"), 413

    # --- Security headers ---
    @app.after_request
    def set_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response

    # --- CLI commands ---
    @app.cli.command("init-db")
    def init_db():
        """Create all database tables."""
        with app.app_context():
            db.create_all()
        click.echo("Database tables created.")

    @app.cli.command("seed-db")
    def seed_db():
        """Populate the database with initial (non-fake) default content."""
        from seed import run_seed
        with app.app_context():
            run_seed()
        click.echo("Database seeded with default content.")

    # Auto-create tables on first run (safe no-op if they already exist)
    with app.app_context():
        db.create_all()

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=app.config["DEBUG"])
