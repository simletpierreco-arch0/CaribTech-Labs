"""
Admin authentication: login, logout, and first-time admin account setup.
"""

from datetime import datetime

from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_user, logout_user, login_required, current_user

from database.extensions import db, limiter
from models import Admin

auth_bp = Blueprint("auth", __name__, url_prefix="/admin")


@auth_bp.route("/setup", methods=["GET", "POST"])
def setup():
    """
    First-time setup: only accessible when no admin account exists yet.
    Prevents the app from shipping with a hardcoded default password.
    """
    if Admin.query.first() is not None:
        flash("Setup has already been completed. Please log in.", "info")
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        email = (request.form.get("email") or "").strip()
        password = request.form.get("password") or ""
        confirm = request.form.get("confirm_password") or ""

        errors = []
        if len(username) < 3:
            errors.append("Username must be at least 3 characters.")
        if "@" not in email:
            errors.append("Please provide a valid email address.")
        if len(password) < 10:
            errors.append("Password must be at least 10 characters long.")
        if password != confirm:
            errors.append("Passwords do not match.")

        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("admin/setup.html")

        admin = Admin(username=username, email=email, full_name=request.form.get("full_name"))
        admin.set_password(password)
        db.session.add(admin)
        db.session.commit()

        flash("Admin account created successfully. Please log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("admin/setup.html")


@auth_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("10 per minute", methods=["POST"])
def login():
    if Admin.query.first() is None:
        return redirect(url_for("auth.setup"))

    if current_user.is_authenticated:
        return redirect(url_for("admin.dashboard"))

    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        remember = bool(request.form.get("remember"))

        admin = Admin.query.filter_by(username=username).first()
        if admin and admin.check_password(password) and admin.is_active_admin:
            login_user(admin, remember=remember)
            admin.last_login = datetime.utcnow()
            db.session.commit()
            session.permanent = True
            next_url = request.args.get("next")
            return redirect(next_url or url_for("admin.dashboard"))

        flash("Invalid username or password.", "error")

    return render_template("admin/login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))
