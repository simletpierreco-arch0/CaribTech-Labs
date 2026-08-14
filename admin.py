"""
Admin dashboard: content management for every editable part of the site.
All routes here require an authenticated admin (see @login_required).
"""

import os
from datetime import datetime, date

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user

from database.extensions import db
from models import (
    SiteSettings, Service, TeamMember, Deal, Post, Media,
    ProjectRequest, ProjectFile, Notification, STATUS_CHOICES, PRIORITY_CHOICES,
    ChatbotSettings, ChatbotFAQ, ChatbotLog, PageView,
)
from utils import save_upload, slugify, unique_slug
from routes.public import PROJECT_TYPES, BUDGET_RANGES, TIMELINES

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.before_request
@login_required
def require_login():
    """Applies @login_required to every route registered on this blueprint."""
    pass


@admin_bp.context_processor
def inject_notifications():
    unread_count = Notification.query.filter_by(is_read=False).count()
    recent_notifications = Notification.query.order_by(Notification.created_at.desc()).limit(8).all()
    return {
        "unread_notif_count": unread_count,
        "recent_notifications": recent_notifications,
        "site_settings": SiteSettings.get_settings(),
    }


# ---------------------------------------------------------------------------
# Dashboard overview
# ---------------------------------------------------------------------------

@admin_bp.route("/")
@admin_bp.route("/dashboard")
def dashboard():
    total_requests = ProjectRequest.query.count()
    new_requests = ProjectRequest.query.filter_by(status="New").count()
    active_projects = ProjectRequest.query.filter(
        ProjectRequest.status.in_(["Planning", "In Progress"])
    ).count()
    team_count = TeamMember.query.filter_by(is_active=True).count()
    published_deals = Deal.query.filter_by(is_active=True).count()
    published_posts = Post.query.filter_by(status="published").count()
    chatbot_conversations = ChatbotLog.query.count()

    recent_requests = ProjectRequest.query.order_by(ProjectRequest.created_at.desc()).limit(5).all()

    # Most requested service types (simple grouping for a small bar chart)
    from sqlalchemy import func
    type_counts = (
        db.session.query(ProjectRequest.project_type, func.count(ProjectRequest.id))
        .group_by(ProjectRequest.project_type)
        .all()
    )

    return render_template(
        "admin/dashboard.html",
        total_requests=total_requests,
        new_requests=new_requests,
        active_projects=active_projects,
        team_count=team_count,
        published_deals=published_deals,
        published_posts=published_posts,
        chatbot_conversations=chatbot_conversations,
        recent_requests=recent_requests,
        type_counts=type_counts,
    )


@admin_bp.route("/notifications/<int:notif_id>/read", methods=["POST"])
def mark_notification_read(notif_id):
    notif = Notification.query.get_or_404(notif_id)
    notif.is_read = True
    db.session.commit()
    return jsonify({"ok": True})


@admin_bp.route("/notifications/read-all", methods=["POST"])
def mark_all_notifications_read():
    Notification.query.filter_by(is_read=False).update({"is_read": True})
    db.session.commit()
    return jsonify({"ok": True})


# ---------------------------------------------------------------------------
# Website content / settings
# ---------------------------------------------------------------------------

@admin_bp.route("/settings", methods=["GET", "POST"])
def settings():
    site = SiteSettings.get_settings()

    if request.method == "POST":
        form = request.form

        site.company_name = form.get("company_name", site.company_name)
        site.tagline = form.get("tagline", site.tagline)
        site.hero_title = form.get("hero_title", site.hero_title)
        site.hero_subtitle = form.get("hero_subtitle", site.hero_subtitle)
        site.hero_button_primary = form.get("hero_button_primary", site.hero_button_primary)
        site.hero_button_secondary = form.get("hero_button_secondary", site.hero_button_secondary)

        site.about_title = form.get("about_title", site.about_title)
        site.about_description = form.get("about_description", site.about_description)
        site.mission = form.get("mission", site.mission)
        site.vision = form.get("vision", site.vision)
        site.values = form.get("values", site.values)

        site.location = form.get("location", site.location)
        site.contact_email = form.get("contact_email") or None
        site.contact_phone = form.get("contact_phone") or None
        site.contact_whatsapp = form.get("contact_whatsapp") or None
        site.website_url = form.get("website_url") or None

        site.social_facebook = form.get("social_facebook") or None
        site.social_instagram = form.get("social_instagram") or None
        site.social_linkedin = form.get("social_linkedin") or None
        site.social_twitter = form.get("social_twitter") or None

        site.footer_text = form.get("footer_text", site.footer_text)
        site.announcement_bar_text = form.get("announcement_bar_text") or None
        site.announcement_bar_active = bool(form.get("announcement_bar_active"))
        site.business_hours = form.get("business_hours") or None

        site.theme_primary_color = form.get("theme_primary_color", site.theme_primary_color)
        site.theme_accent_color = form.get("theme_accent_color", site.theme_accent_color)

        site.maintenance_mode = bool(form.get("maintenance_mode"))

        # Optional logo / about image replacement
        logo_file = request.files.get("logo_upload")
        if logo_file and logo_file.filename:
            path = save_upload(logo_file, "media", current_app.config["ALLOWED_IMAGE_EXTENSIONS"])
            if path:
                site.logo_path = path

        about_img = request.files.get("about_image_upload")
        if about_img and about_img.filename:
            path = save_upload(about_img, "media", current_app.config["ALLOWED_IMAGE_EXTENSIONS"])
            if path:
                site.about_image = path

        db.session.commit()
        flash("Website settings updated successfully.", "success")
        return redirect(url_for("admin.settings"))

    return render_template("admin/settings.html", site=site)


# ---------------------------------------------------------------------------
# Services
# ---------------------------------------------------------------------------

@admin_bp.route("/services")
def services_list():
    services = Service.query.order_by(Service.display_order).all()
    return render_template("admin/services.html", services=services)


@admin_bp.route("/services/new", methods=["POST"])
def services_create():
    name = (request.form.get("name") or "").strip()
    description = (request.form.get("description") or "").strip()
    if not name or not description:
        flash("Service name and description are required.", "error")
        return redirect(url_for("admin.services_list"))

    slug = unique_slug(Service, slugify(name))
    image_path = None
    image_file = request.files.get("image")
    if image_file and image_file.filename:
        image_path = save_upload(image_file, "services", current_app.config["ALLOWED_IMAGE_EXTENSIONS"])

    max_order = db.session.query(db.func.max(Service.display_order)).scalar() or 0

    service = Service(
        name=name,
        slug=slug,
        description=description,
        icon=request.form.get("icon", "cpu"),
        image_path=image_path,
        price_info=request.form.get("price_info") or None,
        cta_text=request.form.get("cta_text", "Start a Project"),
        display_order=max_order + 1,
        is_active=bool(request.form.get("is_active", True)),
    )
    db.session.add(service)
    db.session.commit()
    flash(f'Service "{name}" created.', "success")
    return redirect(url_for("admin.services_list"))


@admin_bp.route("/services/<int:service_id>/edit", methods=["POST"])
def services_edit(service_id):
    service = Service.query.get_or_404(service_id)
    name = (request.form.get("name") or "").strip()
    if name and name != service.name:
        service.slug = unique_slug(Service, slugify(name), exclude_id=service.id)
    service.name = name or service.name
    service.description = request.form.get("description", service.description)
    service.icon = request.form.get("icon", service.icon)
    service.price_info = request.form.get("price_info") or None
    service.cta_text = request.form.get("cta_text", service.cta_text)
    service.is_active = bool(request.form.get("is_active"))

    image_file = request.files.get("image")
    if image_file and image_file.filename:
        path = save_upload(image_file, "services", current_app.config["ALLOWED_IMAGE_EXTENSIONS"])
        if path:
            service.image_path = path

    db.session.commit()
    flash(f'Service "{service.name}" updated.', "success")
    return redirect(url_for("admin.services_list"))


@admin_bp.route("/services/<int:service_id>/delete", methods=["POST"])
def services_delete(service_id):
    service = Service.query.get_or_404(service_id)
    db.session.delete(service)
    db.session.commit()
    flash("Service deleted.", "info")
    return redirect(url_for("admin.services_list"))


@admin_bp.route("/services/reorder", methods=["POST"])
def services_reorder():
    """Expects JSON: {"order": [id1, id2, id3, ...]} in the new display order."""
    data = request.get_json(silent=True) or {}
    order = data.get("order", [])
    for index, service_id in enumerate(order):
        Service.query.filter_by(id=service_id).update({"display_order": index})
    db.session.commit()
    return jsonify({"ok": True})


# ---------------------------------------------------------------------------
# Team members
# ---------------------------------------------------------------------------

@admin_bp.route("/team")
def team_list():
    members = TeamMember.query.order_by(TeamMember.display_order).all()
    return render_template("admin/team.html", members=members)


@admin_bp.route("/team/new", methods=["POST"])
def team_create():
    name = (request.form.get("name") or "").strip()
    position = (request.form.get("position") or "").strip()
    if not name or not position:
        flash("Name and position are required.", "error")
        return redirect(url_for("admin.team_list"))

    photo_path = None
    photo_file = request.files.get("photo")
    if photo_file and photo_file.filename:
        photo_path = save_upload(photo_file, "team", current_app.config["ALLOWED_IMAGE_EXTENSIONS"])

    max_order = db.session.query(db.func.max(TeamMember.display_order)).scalar() or 0

    member = TeamMember(
        name=name,
        position=position,
        bio=request.form.get("bio"),
        skills=request.form.get("skills"),
        photo_path=photo_path,
        linkedin_url=request.form.get("linkedin_url") or None,
        twitter_url=request.form.get("twitter_url") or None,
        github_url=request.form.get("github_url") or None,
        email=request.form.get("email") or None,
        display_order=max_order + 1,
        is_active=bool(request.form.get("is_active", True)),
    )
    db.session.add(member)
    db.session.commit()
    flash(f'Team member "{name}" added.', "success")
    return redirect(url_for("admin.team_list"))


@admin_bp.route("/team/<int:member_id>/edit", methods=["POST"])
def team_edit(member_id):
    member = TeamMember.query.get_or_404(member_id)
    member.name = request.form.get("name", member.name)
    member.position = request.form.get("position", member.position)
    member.bio = request.form.get("bio", member.bio)
    member.skills = request.form.get("skills", member.skills)
    member.linkedin_url = request.form.get("linkedin_url") or None
    member.twitter_url = request.form.get("twitter_url") or None
    member.github_url = request.form.get("github_url") or None
    member.email = request.form.get("email") or None
    member.is_active = bool(request.form.get("is_active"))

    photo_file = request.files.get("photo")
    if photo_file and photo_file.filename:
        path = save_upload(photo_file, "team", current_app.config["ALLOWED_IMAGE_EXTENSIONS"])
        if path:
            member.photo_path = path

    db.session.commit()
    flash(f'Team member "{member.name}" updated.', "success")
    return redirect(url_for("admin.team_list"))


@admin_bp.route("/team/<int:member_id>/delete", methods=["POST"])
def team_delete(member_id):
    member = TeamMember.query.get_or_404(member_id)
    db.session.delete(member)
    db.session.commit()
    flash("Team member removed.", "info")
    return redirect(url_for("admin.team_list"))


@admin_bp.route("/team/reorder", methods=["POST"])
def team_reorder():
    data = request.get_json(silent=True) or {}
    order = data.get("order", [])
    for index, member_id in enumerate(order):
        TeamMember.query.filter_by(id=member_id).update({"display_order": index})
    db.session.commit()
    return jsonify({"ok": True})


# ---------------------------------------------------------------------------
# Deals
# ---------------------------------------------------------------------------

def _parse_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


@admin_bp.route("/deals")
def deals_list():
    deals = Deal.query.order_by(Deal.created_at.desc()).all()
    return render_template("admin/deals.html", deals=deals)


@admin_bp.route("/deals/new", methods=["POST"])
def deals_create():
    title = (request.form.get("title") or "").strip()
    if not title:
        flash("Deal title is required.", "error")
        return redirect(url_for("admin.deals_list"))

    image_path = None
    image_file = request.files.get("image")
    if image_file and image_file.filename:
        image_path = save_upload(image_file, "deals", current_app.config["ALLOWED_IMAGE_EXTENSIONS"])

    deal = Deal(
        title=title,
        description=request.form.get("description"),
        price=request.form.get("price") or None,
        original_price=request.form.get("original_price") or None,
        discount_label=request.form.get("discount_label") or None,
        features=request.form.get("features"),
        image_path=image_path,
        cta_text=request.form.get("cta_text", "Claim This Deal"),
        start_date=_parse_date(request.form.get("start_date")),
        end_date=_parse_date(request.form.get("end_date")),
        is_active=bool(request.form.get("is_active", True)),
    )
    db.session.add(deal)
    db.session.commit()
    flash(f'Deal "{title}" created.', "success")
    return redirect(url_for("admin.deals_list"))


@admin_bp.route("/deals/<int:deal_id>/edit", methods=["POST"])
def deals_edit(deal_id):
    deal = Deal.query.get_or_404(deal_id)
    deal.title = request.form.get("title", deal.title)
    deal.description = request.form.get("description", deal.description)
    deal.price = request.form.get("price") or None
    deal.original_price = request.form.get("original_price") or None
    deal.discount_label = request.form.get("discount_label") or None
    deal.features = request.form.get("features", deal.features)
    deal.cta_text = request.form.get("cta_text", deal.cta_text)
    deal.start_date = _parse_date(request.form.get("start_date"))
    deal.end_date = _parse_date(request.form.get("end_date"))
    deal.is_active = bool(request.form.get("is_active"))

    image_file = request.files.get("image")
    if image_file and image_file.filename:
        path = save_upload(image_file, "deals", current_app.config["ALLOWED_IMAGE_EXTENSIONS"])
        if path:
            deal.image_path = path

    db.session.commit()
    flash(f'Deal "{deal.title}" updated.', "success")
    return redirect(url_for("admin.deals_list"))


@admin_bp.route("/deals/<int:deal_id>/delete", methods=["POST"])
def deals_delete(deal_id):
    deal = Deal.query.get_or_404(deal_id)
    db.session.delete(deal)
    db.session.commit()
    flash("Deal deleted.", "info")
    return redirect(url_for("admin.deals_list"))


@admin_bp.route("/deals/<int:deal_id>/toggle", methods=["POST"])
def deals_toggle(deal_id):
    deal = Deal.query.get_or_404(deal_id)
    deal.is_active = not deal.is_active
    db.session.commit()
    return jsonify({"ok": True, "is_active": deal.is_active})


# ---------------------------------------------------------------------------
# Posts / announcements
# ---------------------------------------------------------------------------

@admin_bp.route("/posts")
def posts_list():
    posts = Post.query.order_by(Post.created_at.desc()).all()
    return render_template("admin/posts.html", posts=posts)


@admin_bp.route("/posts/new", methods=["POST"])
def posts_create():
    title = (request.form.get("title") or "").strip()
    content = (request.form.get("content") or "").strip()
    if not title or not content:
        flash("Post title and content are required.", "error")
        return redirect(url_for("admin.posts_list"))

    slug = unique_slug(Post, slugify(title))
    status = request.form.get("status", "draft")

    image_path = None
    image_file = request.files.get("featured_image")
    if image_file and image_file.filename:
        image_path = save_upload(image_file, "posts", current_app.config["ALLOWED_IMAGE_EXTENSIONS"])

    post = Post(
        title=title,
        slug=slug,
        content=content,
        excerpt=request.form.get("excerpt") or None,
        featured_image=image_path,
        category=request.form.get("category") or None,
        status=status,
        published_at=datetime.utcnow() if status == "published" else None,
    )
    db.session.add(post)
    db.session.commit()
    flash(f'Post "{title}" created.', "success")
    return redirect(url_for("admin.posts_list"))


@admin_bp.route("/posts/<int:post_id>/edit", methods=["POST"])
def posts_edit(post_id):
    post = Post.query.get_or_404(post_id)
    new_title = request.form.get("title", post.title)
    if new_title != post.title:
        post.slug = unique_slug(Post, slugify(new_title), exclude_id=post.id)
    post.title = new_title
    post.content = request.form.get("content", post.content)
    post.excerpt = request.form.get("excerpt") or None
    post.category = request.form.get("category") or None

    new_status = request.form.get("status", post.status)
    if new_status == "published" and post.status != "published":
        post.published_at = datetime.utcnow()
    post.status = new_status

    image_file = request.files.get("featured_image")
    if image_file and image_file.filename:
        path = save_upload(image_file, "posts", current_app.config["ALLOWED_IMAGE_EXTENSIONS"])
        if path:
            post.featured_image = path

    db.session.commit()
    flash(f'Post "{post.title}" updated.', "success")
    return redirect(url_for("admin.posts_list"))


@admin_bp.route("/posts/<int:post_id>/delete", methods=["POST"])
def posts_delete(post_id):
    post = Post.query.get_or_404(post_id)
    db.session.delete(post)
    db.session.commit()
    flash("Post deleted.", "info")
    return redirect(url_for("admin.posts_list"))


# ---------------------------------------------------------------------------
# Media library
# ---------------------------------------------------------------------------

@admin_bp.route("/media")
def media_list():
    media_items = Media.query.order_by(Media.created_at.desc()).all()
    return render_template("admin/media.html", media_items=media_items)


@admin_bp.route("/media/upload", methods=["POST"])
def media_upload():
    files = request.files.getlist("files")
    allowed_ext = current_app.config["ALLOWED_IMAGE_EXTENSIONS"]
    uploaded = 0
    for f in files:
        if f and f.filename:
            rel_path = save_upload(f, "media", allowed_ext)
            if rel_path:
                size = None
                try:
                    size = os.path.getsize(os.path.join(current_app.root_path, "static", rel_path))
                except OSError:
                    pass
                db.session.add(Media(
                    filename=rel_path.rsplit("/", 1)[-1],
                    original_filename=f.filename,
                    file_path=rel_path,
                    file_type=rel_path.rsplit(".", 1)[-1],
                    file_size=size,
                    uploaded_by=current_user.id,
                    category=request.form.get("category", "general"),
                ))
                uploaded += 1
    db.session.commit()
    if uploaded:
        flash(f"{uploaded} file(s) uploaded to the media library.", "success")
    else:
        flash("No valid files were uploaded.", "error")
    return redirect(url_for("admin.media_list"))


@admin_bp.route("/media/<int:media_id>/delete", methods=["POST"])
def media_delete(media_id):
    item = Media.query.get_or_404(media_id)
    try:
        full_path = os.path.join(current_app.root_path, "static", item.file_path)
        if os.path.exists(full_path):
            os.remove(full_path)
    except OSError:
        pass
    db.session.delete(item)
    db.session.commit()
    flash("File deleted from media library.", "info")
    return redirect(url_for("admin.media_list"))


# ---------------------------------------------------------------------------
# Project requests (client submissions)
# ---------------------------------------------------------------------------

@admin_bp.route("/requests")
def requests_list():
    status_filter = request.args.get("status")
    priority_filter = request.args.get("priority")
    search_q = request.args.get("q", "").strip()

    query = ProjectRequest.query
    if status_filter:
        query = query.filter_by(status=status_filter)
    if priority_filter:
        query = query.filter_by(priority=priority_filter)
    if search_q:
        like = f"%{search_q}%"
        query = query.filter(
            db.or_(
                ProjectRequest.full_name.ilike(like),
                ProjectRequest.business_name.ilike(like),
                ProjectRequest.email.ilike(like),
                ProjectRequest.project_title.ilike(like),
            )
        )

    requests_ = query.order_by(ProjectRequest.created_at.desc()).all()
    return render_template(
        "admin/requests.html",
        requests=requests_,
        status_choices=STATUS_CHOICES,
        priority_choices=PRIORITY_CHOICES,
        current_status=status_filter,
        current_priority=priority_filter,
        search_q=search_q,
    )


@admin_bp.route("/requests/<int:request_id>")
def requests_detail(request_id):
    project_request = ProjectRequest.query.get_or_404(request_id)
    return render_template(
        "admin/request_detail.html",
        project_request=project_request,
        status_choices=STATUS_CHOICES,
        priority_choices=PRIORITY_CHOICES,
    )


@admin_bp.route("/requests/<int:request_id>/update", methods=["POST"])
def requests_update(request_id):
    project_request = ProjectRequest.query.get_or_404(request_id)
    new_status = request.form.get("status")
    new_priority = request.form.get("priority")
    notes = request.form.get("internal_notes")

    if new_status in STATUS_CHOICES:
        project_request.status = new_status
    if new_priority in PRIORITY_CHOICES:
        project_request.priority = new_priority
    if notes is not None:
        project_request.internal_notes = notes

    db.session.commit()
    flash("Project request updated.", "success")
    return redirect(url_for("admin.requests_detail", request_id=request_id))


@admin_bp.route("/requests/<int:request_id>/delete", methods=["POST"])
def requests_delete(request_id):
    project_request = ProjectRequest.query.get_or_404(request_id)
    db.session.delete(project_request)
    db.session.commit()
    flash("Project request deleted.", "info")
    return redirect(url_for("admin.requests_list"))


# ---------------------------------------------------------------------------
# Chatbot management
# ---------------------------------------------------------------------------

@admin_bp.route("/chatbot", methods=["GET", "POST"])
def chatbot_settings():
    settings = ChatbotSettings.get_settings()

    if request.method == "POST":
        settings.is_enabled = bool(request.form.get("is_enabled"))
        settings.bot_name = request.form.get("bot_name", settings.bot_name)
        settings.welcome_message = request.form.get("welcome_message", settings.welcome_message)
        settings.fallback_message = request.form.get("fallback_message", settings.fallback_message)
        settings.suggested_questions = request.form.get("suggested_questions", settings.suggested_questions)

        avatar_file = request.files.get("avatar")
        if avatar_file and avatar_file.filename:
            path = save_upload(avatar_file, "media", current_app.config["ALLOWED_IMAGE_EXTENSIONS"])
            if path:
                settings.avatar_path = path

        db.session.commit()
        flash("Chatbot settings updated.", "success")
        return redirect(url_for("admin.chatbot_settings"))

    faqs = ChatbotFAQ.query.order_by(ChatbotFAQ.display_order).all()
    recent_logs = ChatbotLog.query.order_by(ChatbotLog.created_at.desc()).limit(20).all()
    total_conversations = ChatbotLog.query.count()
    return render_template(
        "admin/chatbot.html", settings=settings, faqs=faqs,
        recent_logs=recent_logs, total_conversations=total_conversations,
    )


@admin_bp.route("/chatbot/faqs/new", methods=["POST"])
def chatbot_faq_create():
    keywords = (request.form.get("keywords") or "").strip()
    answer = (request.form.get("answer") or "").strip()
    if not keywords or not answer:
        flash("Keywords and answer are required for a chatbot FAQ.", "error")
        return redirect(url_for("admin.chatbot_settings"))

    max_order = db.session.query(db.func.max(ChatbotFAQ.display_order)).scalar() or 0
    faq = ChatbotFAQ(
        keywords=keywords,
        question_label=request.form.get("question_label") or None,
        answer=answer,
        show_cta=bool(request.form.get("show_cta")),
        display_order=max_order + 1,
        is_active=bool(request.form.get("is_active", True)),
    )
    db.session.add(faq)
    db.session.commit()
    flash("FAQ response added.", "success")
    return redirect(url_for("admin.chatbot_settings"))


@admin_bp.route("/chatbot/faqs/<int:faq_id>/edit", methods=["POST"])
def chatbot_faq_edit(faq_id):
    faq = ChatbotFAQ.query.get_or_404(faq_id)
    faq.keywords = request.form.get("keywords", faq.keywords)
    faq.question_label = request.form.get("question_label") or None
    faq.answer = request.form.get("answer", faq.answer)
    faq.show_cta = bool(request.form.get("show_cta"))
    faq.is_active = bool(request.form.get("is_active"))
    db.session.commit()
    flash("FAQ response updated.", "success")
    return redirect(url_for("admin.chatbot_settings"))


@admin_bp.route("/chatbot/faqs/<int:faq_id>/delete", methods=["POST"])
def chatbot_faq_delete(faq_id):
    faq = ChatbotFAQ.query.get_or_404(faq_id)
    db.session.delete(faq)
    db.session.commit()
    flash("FAQ response removed.", "info")
    return redirect(url_for("admin.chatbot_settings"))


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------

@admin_bp.route("/analytics")
def analytics():
    from sqlalchemy import func

    total_views = PageView.query.count()
    top_pages = (
        db.session.query(PageView.path, func.count(PageView.id).label("views"))
        .group_by(PageView.path)
        .order_by(func.count(PageView.id).desc())
        .limit(10)
        .all()
    )
    total_requests = ProjectRequest.query.count()
    requests_by_type = (
        db.session.query(ProjectRequest.project_type, func.count(ProjectRequest.id))
        .group_by(ProjectRequest.project_type)
        .all()
    )
    total_chatbot = ChatbotLog.query.count()
    unanswered_chatbot = ChatbotLog.query.filter_by(matched_faq_id=None).count()
    total_deal_clicks = db.session.query(func.sum(Deal.click_count)).scalar() or 0

    return render_template(
        "admin/analytics.html",
        total_views=total_views,
        top_pages=top_pages,
        total_requests=total_requests,
        requests_by_type=requests_by_type,
        total_chatbot=total_chatbot,
        unanswered_chatbot=unanswered_chatbot,
        total_deal_clicks=total_deal_clicks,
    )
