"""
Public-facing routes: home, about, services, team, deals, contact, project request, chatbot API.
"""

from datetime import datetime, date

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app

from database.extensions import db, limiter
from models import (
    SiteSettings, Service, TeamMember, Deal, Post, ProjectRequest, ProjectFile,
    Notification, ChatbotSettings, ChatbotFAQ, ChatbotLog, PageView,
)
from utils import save_upload

public_bp = Blueprint("public", __name__)


def _track_view(path):
    try:
        db.session.add(PageView(path=path))
        db.session.commit()
    except Exception:
        db.session.rollback()


@public_bp.before_app_request
def check_maintenance_mode():
    """Redirect visitors to a maintenance page when enabled, but never block /admin."""
    if request.path.startswith("/admin") or request.path.startswith("/static"):
        return None
    settings = SiteSettings.get_settings()
    if settings.maintenance_mode:
        return render_template("maintenance.html", settings=settings), 503


@public_bp.context_processor
def inject_settings():
    """Make site-wide settings available in every public template without passing manually."""
    return {"site_settings": SiteSettings.get_settings()}


@public_bp.route("/")
def home():
    settings = SiteSettings.get_settings()
    services = Service.query.filter_by(is_active=True).order_by(Service.display_order).limit(6).all()
    deals = [d for d in Deal.query.filter_by(is_active=True).all() if d.is_live()][:3]
    posts = Post.query.filter_by(status="published").order_by(Post.published_at.desc()).limit(3).all()
    _track_view("/")
    return render_template("index.html", settings=settings, services=services, deals=deals, posts=posts)


@public_bp.route("/about")
def about():
    settings = SiteSettings.get_settings()
    _track_view("/about")
    return render_template("about.html", settings=settings)


@public_bp.route("/services")
def services():
    settings = SiteSettings.get_settings()
    all_services = Service.query.filter_by(is_active=True).order_by(Service.display_order).all()
    _track_view("/services")
    return render_template("services.html", settings=settings, services=all_services)


@public_bp.route("/team")
def team():
    settings = SiteSettings.get_settings()
    members = TeamMember.query.filter_by(is_active=True).order_by(TeamMember.display_order).all()
    _track_view("/team")
    return render_template("team.html", settings=settings, members=members)


@public_bp.route("/deals")
def deals():
    settings = SiteSettings.get_settings()
    all_deals = Deal.query.filter_by(is_active=True).order_by(Deal.created_at.desc()).all()
    live_deals = [d for d in all_deals if d.is_live()]
    _track_view("/deals")
    return render_template("deals.html", settings=settings, deals=live_deals)


@public_bp.route("/deals/<int:deal_id>/click", methods=["POST"])
@limiter.limit("30 per minute")
def deal_click(deal_id):
    deal = Deal.query.get_or_404(deal_id)
    deal.click_count = (deal.click_count or 0) + 1
    db.session.commit()
    return jsonify({"ok": True})


@public_bp.route("/news")
def news():
    settings = SiteSettings.get_settings()
    posts = Post.query.filter_by(status="published").order_by(Post.published_at.desc()).all()
    return render_template("news.html", settings=settings, posts=posts)


@public_bp.route("/news/<slug>")
def news_detail(slug):
    settings = SiteSettings.get_settings()
    post = Post.query.filter_by(slug=slug, status="published").first_or_404()
    return render_template("news_detail.html", settings=settings, post=post)


@public_bp.route("/contact")
def contact():
    settings = SiteSettings.get_settings()
    _track_view("/contact")
    return render_template("contact.html", settings=settings)


PROJECT_TYPES = ["Website", "AI Chatbot", "Web Application", "Business Automation", "Dashboard", "AI Integration", "Other"]
BUDGET_RANGES = ["Under $500", "$500 - $1,500", "$1,500 - $5,000", "$5,000+", "Not sure yet"]
TIMELINES = ["ASAP", "1-2 weeks", "1 month", "1-3 months", "Flexible"]
CONTACT_METHODS = ["Email", "Phone", "WhatsApp"]


@public_bp.route("/request", methods=["GET", "POST"])
@limiter.limit("10 per hour", methods=["POST"])
def request_project():
    settings = SiteSettings.get_settings()

    if request.method == "POST":
        full_name = (request.form.get("full_name") or "").strip()
        email = (request.form.get("email") or "").strip()
        description = (request.form.get("description") or "").strip()
        project_type = request.form.get("project_type") or "Other"

        errors = []
        if not full_name:
            errors.append("Full name is required.")
        if not email or "@" not in email:
            errors.append("A valid email address is required.")
        if not description:
            errors.append("Please describe your project.")

        if errors:
            for e in errors:
                flash(e, "error")
            return render_template(
                "request.html", settings=settings, project_types=PROJECT_TYPES,
                budget_ranges=BUDGET_RANGES, timelines=TIMELINES, contact_methods=CONTACT_METHODS,
                form=request.form,
            )

        new_request = ProjectRequest(
            full_name=full_name,
            business_name=request.form.get("business_name"),
            email=email,
            phone=request.form.get("phone"),
            preferred_contact_method=request.form.get("preferred_contact_method", "Email"),
            project_type=project_type,
            project_title=request.form.get("project_title"),
            description=description,
            main_goals=request.form.get("main_goals"),
            target_audience=request.form.get("target_audience"),
            desired_features=request.form.get("desired_features"),
            budget_range=request.form.get("budget_range"),
            timeline=request.form.get("timeline"),
            additional_info=request.form.get("additional_info"),
        )
        db.session.add(new_request)
        db.session.flush()  # get new_request.id before commit

        # Handle optional file uploads (multiple files allowed)
        files = request.files.getlist("attachments")
        allowed_ext = current_app.config["ALLOWED_IMAGE_EXTENSIONS"] | current_app.config["ALLOWED_DOCUMENT_EXTENSIONS"]
        for f in files:
            if f and f.filename:
                rel_path = save_upload(f, "requests", allowed_ext)
                if rel_path:
                    db.session.add(ProjectFile(
                        request_id=new_request.id,
                        filename=rel_path.rsplit("/", 1)[-1],
                        original_filename=f.filename,
                        file_path=rel_path,
                    ))

        db.session.add(Notification(
            message=f"New project request from {full_name} ({project_type})",
            link=f"/admin/requests/{new_request.id}",
            notif_type="request",
        ))

        db.session.commit()
        return redirect(url_for("public.request_confirmation", request_id=new_request.id))

    return render_template(
        "request.html", settings=settings, project_types=PROJECT_TYPES,
        budget_ranges=BUDGET_RANGES, timelines=TIMELINES, contact_methods=CONTACT_METHODS, form={},
    )


@public_bp.route("/request/confirmation/<int:request_id>")
def request_confirmation(request_id):
    settings = SiteSettings.get_settings()
    project_request = ProjectRequest.query.get_or_404(request_id)
    return render_template("confirmation.html", settings=settings, project_request=project_request)


# ---------------------------------------------------------------------------
# Chatbot API (simple keyword-matching bot backed by admin-editable FAQs)
# ---------------------------------------------------------------------------

@public_bp.route("/api/chatbot/init")
def chatbot_init():
    settings = ChatbotSettings.get_settings()
    if not settings.is_enabled:
        return jsonify({"enabled": False})
    return jsonify({
        "enabled": True,
        "bot_name": settings.bot_name,
        "welcome_message": settings.welcome_message,
        "avatar_path": settings.avatar_path,
        "suggested_questions": settings.suggested_questions_list(),
    })


@public_bp.route("/api/chatbot/message", methods=["POST"])
@limiter.limit("60 per minute")
def chatbot_message():
    settings = ChatbotSettings.get_settings()
    if not settings.is_enabled:
        return jsonify({"error": "Chatbot is currently disabled."}), 403

    data = request.get_json(silent=True) or {}
    user_message = (data.get("message") or "").strip()
    if not user_message:
        return jsonify({"error": "Empty message."}), 400

    lowered = user_message.lower()
    faqs = ChatbotFAQ.query.filter_by(is_active=True).order_by(ChatbotFAQ.display_order).all()

    best_match = None
    best_score = 0
    for faq in faqs:
        score = sum(1 for kw in faq.keywords_list() if kw in lowered)
        if score > best_score:
            best_score = score
            best_match = faq

    if best_match and best_score > 0:
        answer = best_match.answer
        show_cta = best_match.show_cta
        matched_id = best_match.id
    else:
        answer = settings.fallback_message
        show_cta = True
        matched_id = None

    try:
        db.session.add(ChatbotLog(user_message=user_message[:500], matched_faq_id=matched_id))
        db.session.commit()
    except Exception:
        db.session.rollback()

    return jsonify({"answer": answer, "show_cta": show_cta})
