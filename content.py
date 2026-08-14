"""
Content models - everything the admin can edit to control the public site.
"""

from datetime import datetime
from database.extensions import db


class SiteSettings(db.Model):
    """
    Singleton-style table (we only ever use row id=1) holding all
    site-wide editable text/config so nothing is hardcoded in HTML.
    """
    __tablename__ = "site_settings"

    id = db.Column(db.Integer, primary_key=True)

    # Branding
    company_name = db.Column(db.String(150), default="CaribTech Labs")
    tagline = db.Column(db.String(255), default="Building Digital Solutions for the Caribbean.")
    logo_path = db.Column(db.String(255), default="images/Caribtech_logo.png")

    # Hero section
    hero_title = db.Column(db.String(255), default="Building Digital Solutions for the Caribbean.")
    hero_subtitle = db.Column(
        db.Text,
        default="We design websites, AI-powered solutions, applications, and digital "
        "systems that help businesses work smarter and serve their customers better.",
    )
    hero_button_primary = db.Column(db.String(80), default="Start a Project")
    hero_button_secondary = db.Column(db.String(80), default="Explore Our Services")

    # About section
    about_title = db.Column(db.String(255), default="About CaribTech Labs")
    about_description = db.Column(db.Text, default="")
    mission = db.Column(db.Text, default="")
    vision = db.Column(db.Text, default="")
    values = db.Column(db.Text, default="")
    about_image = db.Column(db.String(255), nullable=True)

    # Location / contact (left blank on purpose - never invented)
    location = db.Column(db.String(255), default="Saint Vincent and the Grenadines / Online")
    contact_email = db.Column(db.String(150), nullable=True)
    contact_phone = db.Column(db.String(50), nullable=True)
    contact_whatsapp = db.Column(db.String(50), nullable=True)
    website_url = db.Column(db.String(255), nullable=True)

    # Social links
    social_facebook = db.Column(db.String(255), nullable=True)
    social_instagram = db.Column(db.String(255), nullable=True)
    social_linkedin = db.Column(db.String(255), nullable=True)
    social_twitter = db.Column(db.String(255), nullable=True)

    # Footer / misc
    footer_text = db.Column(db.Text, default="Building Digital Solutions for the Caribbean.")
    announcement_bar_text = db.Column(db.String(255), nullable=True)
    announcement_bar_active = db.Column(db.Boolean, default=False)

    # Business hours (simple free-text so admin can phrase however they like)
    business_hours = db.Column(db.String(255), nullable=True)

    # Theme
    theme_primary_color = db.Column(db.String(20), default="#0B1F3A")   # deep navy
    theme_accent_color = db.Column(db.String(20), default="#17B7D6")    # Caribbean cyan

    # System toggles
    maintenance_mode = db.Column(db.Boolean, default=False)

    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @staticmethod
    def get_settings():
        """Return the single settings row, creating it with defaults if missing."""
        settings = SiteSettings.query.first()
        if not settings:
            settings = SiteSettings()
            db.session.add(settings)
            db.session.commit()
        return settings


class Service(db.Model):
    __tablename__ = "services"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    slug = db.Column(db.String(170), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=False)
    icon = db.Column(db.String(80), default="cpu")  # icon name/key used by the frontend
    image_path = db.Column(db.String(255), nullable=True)
    price_info = db.Column(db.String(150), nullable=True)  # e.g. "Starting at $500"
    cta_text = db.Column(db.String(80), default="Start a Project")
    display_order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Service {self.name}>"


class TeamMember(db.Model):
    __tablename__ = "team_members"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    position = db.Column(db.String(150), nullable=False)
    bio = db.Column(db.Text, nullable=True)
    skills = db.Column(db.String(500), nullable=True)  # comma-separated
    photo_path = db.Column(db.String(255), nullable=True)
    linkedin_url = db.Column(db.String(255), nullable=True)
    twitter_url = db.Column(db.String(255), nullable=True)
    github_url = db.Column(db.String(255), nullable=True)
    email = db.Column(db.String(150), nullable=True)
    display_order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def skills_list(self):
        if not self.skills:
            return []
        return [s.strip() for s in self.skills.split(",") if s.strip()]

    def __repr__(self):
        return f"<TeamMember {self.name}>"


class Deal(db.Model):
    __tablename__ = "deals"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.String(50), nullable=True)
    original_price = db.Column(db.String(50), nullable=True)
    discount_label = db.Column(db.String(50), nullable=True)  # e.g. "20% OFF"
    features = db.Column(db.Text, nullable=True)  # newline-separated bullet features
    image_path = db.Column(db.String(255), nullable=True)
    cta_text = db.Column(db.String(80), default="Claim This Deal")
    start_date = db.Column(db.Date, nullable=True)
    end_date = db.Column(db.Date, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    click_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def features_list(self):
        if not self.features:
            return []
        return [f.strip() for f in self.features.splitlines() if f.strip()]

    def is_expired(self):
        from datetime import date
        return bool(self.end_date and self.end_date < date.today())

    def is_upcoming(self):
        from datetime import date
        return bool(self.start_date and self.start_date > date.today())

    def is_live(self):
        return self.is_active and not self.is_expired() and not self.is_upcoming()

    def __repr__(self):
        return f"<Deal {self.title}>"


class Post(db.Model):
    __tablename__ = "posts"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(220), unique=True, nullable=False)
    content = db.Column(db.Text, nullable=False)
    excerpt = db.Column(db.String(300), nullable=True)
    featured_image = db.Column(db.String(255), nullable=True)
    category = db.Column(db.String(80), nullable=True)
    status = db.Column(db.String(20), default="draft")  # draft | published
    published_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Post {self.title}>"


class Media(db.Model):
    __tablename__ = "media"

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=True)
    file_path = db.Column(db.String(255), nullable=False)  # relative to /static
    file_type = db.Column(db.String(50), nullable=True)
    file_size = db.Column(db.Integer, nullable=True)  # bytes
    uploaded_by = db.Column(db.Integer, db.ForeignKey("admins.id"), nullable=True)
    category = db.Column(db.String(50), nullable=True)  # team | service | deal | post | general
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Media {self.filename}>"
