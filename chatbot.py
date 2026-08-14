"""
Chatbot models - admin-editable FAQ/rules-based chatbot (no external AI API required).
"""

from datetime import datetime
from database.extensions import db


class ChatbotSettings(db.Model):
    __tablename__ = "chatbot_settings"

    id = db.Column(db.Integer, primary_key=True)
    is_enabled = db.Column(db.Boolean, default=True)
    bot_name = db.Column(db.String(80), default="CaribTech Assistant")
    welcome_message = db.Column(
        db.Text,
        default="Hi! I'm the CaribTech Labs assistant. Ask me about our services, "
        "how to start a project, or anything else about the company.",
    )
    avatar_path = db.Column(db.String(255), nullable=True)
    fallback_message = db.Column(
        db.Text,
        default="I'm not sure about that yet, but our team can help directly. "
        "Would you like to start a project request?",
    )
    suggested_questions = db.Column(
        db.Text,
        default="What services do you offer?\nHow can I start a project?\n"
        "Do you build AI chatbots?\nWhere are you located?\n"
        "What types of businesses do you work with?",
    )

    @staticmethod
    def get_settings():
        settings = ChatbotSettings.query.first()
        if not settings:
            settings = ChatbotSettings()
            db.session.add(settings)
            db.session.commit()
        return settings

    def suggested_questions_list(self):
        if not self.suggested_questions:
            return []
        return [q.strip() for q in self.suggested_questions.splitlines() if q.strip()]


class ChatbotFAQ(db.Model):
    __tablename__ = "chatbot_faqs"

    id = db.Column(db.Integer, primary_key=True)
    # Comma-separated trigger keywords/phrases matched against user messages
    keywords = db.Column(db.String(500), nullable=False)
    question_label = db.Column(db.String(255), nullable=True)  # shown as a suggested chip
    answer = db.Column(db.Text, nullable=False)
    show_cta = db.Column(db.Boolean, default=False)  # show "Start a Project" button with answer
    display_order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def keywords_list(self):
        return [k.strip().lower() for k in self.keywords.split(",") if k.strip()]


class ChatbotLog(db.Model):
    """Lightweight internal analytics for chatbot usage (no invasive tracking)."""
    __tablename__ = "chatbot_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_message = db.Column(db.String(500), nullable=False)
    matched_faq_id = db.Column(db.Integer, db.ForeignKey("chatbot_faqs.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class PageView(db.Model):
    """Minimal, privacy-respecting page view counter (no cookies/fingerprinting)."""
    __tablename__ = "page_views"

    id = db.Column(db.Integer, primary_key=True)
    path = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
