"""
Shared helper functions: secure file uploads, slug generation, decorators.
"""

import os
import re
import uuid
from functools import wraps

from flask import current_app, abort
from flask_login import current_user
from werkzeug.utils import secure_filename


def allowed_file(filename, extensions):
    if "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in extensions


def save_upload(file_storage, subfolder, allowed_extensions):
    """
    Securely save an uploaded file under static/uploads/<subfolder>/.
    Returns the relative path (for storing in the DB) or None if invalid.
    """
    if not file_storage or file_storage.filename == "":
        return None

    original_name = secure_filename(file_storage.filename)
    if not allowed_file(original_name, allowed_extensions):
        return None

    ext = original_name.rsplit(".", 1)[1].lower()
    unique_name = f"{uuid.uuid4().hex}.{ext}"

    target_dir = os.path.join(current_app.config["UPLOAD_FOLDER"], subfolder)
    os.makedirs(target_dir, exist_ok=True)

    file_storage.save(os.path.join(target_dir, unique_name))

    # Path relative to /static, for use in url_for('static', filename=...)
    return f"uploads/{subfolder}/{unique_name}"


def slugify(text):
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text or uuid.uuid4().hex[:8]


def unique_slug(model, base_slug, exclude_id=None):
    """Ensure slug uniqueness by appending a numeric suffix if needed."""
    slug = base_slug
    counter = 2
    while True:
        query = model.query.filter_by(slug=slug)
        if exclude_id:
            query = query.filter(model.id != exclude_id)
        if not query.first():
            return slug
        slug = f"{base_slug}-{counter}"
        counter += 1


def admin_required(f):
    """Extra explicit guard on top of @login_required for clarity in admin routes."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            abort(401)
        return f(*args, **kwargs)
    return decorated
