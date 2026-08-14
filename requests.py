"""
Models for the "Start a Project" client-facing form and the admin's
internal handling of those requests.
"""

from datetime import datetime
from database.extensions import db

STATUS_CHOICES = ["New", "Reviewing", "Contacted", "Planning", "In Progress", "Completed", "Cancelled"]
PRIORITY_CHOICES = ["Low", "Normal", "High", "Urgent"]


class ProjectRequest(db.Model):
    __tablename__ = "project_requests"

    id = db.Column(db.Integer, primary_key=True)

    # Contact information
    full_name = db.Column(db.String(150), nullable=False)
    business_name = db.Column(db.String(150), nullable=True)
    email = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(50), nullable=True)
    preferred_contact_method = db.Column(db.String(30), default="Email")

    # Project information
    project_type = db.Column(db.String(80), nullable=False)
    project_title = db.Column(db.String(200), nullable=True)
    description = db.Column(db.Text, nullable=False)
    main_goals = db.Column(db.Text, nullable=True)
    target_audience = db.Column(db.String(255), nullable=True)
    desired_features = db.Column(db.Text, nullable=True)

    budget_range = db.Column(db.String(80), nullable=True)
    timeline = db.Column(db.String(50), nullable=True)
    additional_info = db.Column(db.Text, nullable=True)

    # Internal management
    status = db.Column(db.String(30), default="New")
    priority = db.Column(db.String(20), default="Normal")
    internal_notes = db.Column(db.Text, nullable=True)  # never shown publicly

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    files = db.relationship("ProjectFile", backref="request", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<ProjectRequest {self.id} - {self.full_name}>"


class ProjectFile(db.Model):
    __tablename__ = "project_files"

    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey("project_requests.id"), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=True)
    file_path = db.Column(db.String(255), nullable=False)
    file_size = db.Column(db.Integer, nullable=True)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)


class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.String(255), nullable=False)
    link = db.Column(db.String(255), nullable=True)
    notif_type = db.Column(db.String(50), default="info")  # info | request | system
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
