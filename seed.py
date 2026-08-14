"""
Seeds the database with CaribTech Labs' real default content: the seven
services actually offered, chatbot settings/FAQs, and base site settings.

This does NOT create fake testimonials, fake stats, or fake contact info -
those fields are left blank/editable per the project requirements.
"""

from database.extensions import db
from models import SiteSettings, Service, ChatbotSettings, ChatbotFAQ
from utils import slugify, unique_slug

DEFAULT_SERVICES = [
    {
        "name": "Website Development",
        "icon": "layout",
        "description": "Modern responsive websites for businesses and organizations.",
    },
    {
        "name": "AI Chatbots",
        "icon": "message-circle",
        "description": "Customer-service and information assistants.",
    },
    {
        "name": "Web Applications",
        "icon": "code",
        "description": "Custom web-based software.",
    },
    {
        "name": "Business Automation",
        "icon": "zap",
        "description": "Systems that reduce repetitive work.",
    },
    {
        "name": "Customer Service Solutions",
        "icon": "headphones",
        "description": "Digital tools that improve customer interaction.",
    },
    {
        "name": "Business Dashboards",
        "icon": "bar-chart-2",
        "description": "Centralized dashboards for business information.",
    },
    {
        "name": "AI Integration",
        "icon": "cpu",
        "description": "Adding useful AI capabilities to existing business systems.",
    },
]

DEFAULT_FAQS = [
    {
        "keywords": "service,services,offer,do you build,what do you do",
        "question_label": "What services do you offer?",
        "answer": "We offer website development, AI chatbots, web applications, business "
        "automation, customer service solutions, business dashboards, and AI integration. "
        "Take a look at our Services page for details on each.",
        "show_cta": True,
    },
    {
        "keywords": "start,project,begin,how do i start,get started,hire",
        "question_label": "How can I start a project?",
        "answer": "You can start by filling out our Project Request form - just tell us about "
        "your business and what you're looking for, and our team will follow up with you.",
        "show_cta": True,
    },
    {
        "keywords": "chatbot,ai bot,build a bot,chat assistant",
        "question_label": "Do you build AI chatbots?",
        "answer": "Yes! AI chatbots and AI assistants are one of our core services. We can build "
        "one tailored to your business, just like this one.",
        "show_cta": True,
    },
    {
        "keywords": "located,location,where are you,based,address",
        "question_label": "Where are you located?",
        "answer": "CaribTech Labs is based in Saint Vincent and the Grenadines, and we work "
        "with clients online across the Caribbean and beyond.",
        "show_cta": False,
    },
    {
        "keywords": "business,type of client,who do you work with,industries",
        "question_label": "What types of businesses do you work with?",
        "answer": "We work with businesses and organizations of many kinds across the Caribbean "
        "that want to modernize with websites, AI tools, and digital systems.",
        "show_cta": True,
    },
    {
        "keywords": "deal,deals,offer,discount,promotion,package",
        "question_label": "Do you have any current deals?",
        "answer": "Check out our Deals page for current packages and offers. Availability "
        "changes, so it's worth a look.",
        "show_cta": False,
    },
    {
        "keywords": "team,who works,staff,founder",
        "question_label": "Who is on the team?",
        "answer": "You can meet the CaribTech Labs team on our Our Team page.",
        "show_cta": False,
    },
]


def run_seed():
    # Site settings (creates the row if missing; does not overwrite existing edits)
    SiteSettings.get_settings()

    # Services - only add if the table is empty, so re-running seed is safe
    if Service.query.count() == 0:
        for index, item in enumerate(DEFAULT_SERVICES):
            slug = unique_slug(Service, slugify(item["name"]))
            db.session.add(Service(
                name=item["name"],
                slug=slug,
                description=item["description"],
                icon=item["icon"],
                display_order=index,
                is_active=True,
            ))

    # Chatbot settings + FAQs
    ChatbotSettings.get_settings()
    if ChatbotFAQ.query.count() == 0:
        for index, item in enumerate(DEFAULT_FAQS):
            db.session.add(ChatbotFAQ(
                keywords=item["keywords"],
                question_label=item["question_label"],
                answer=item["answer"],
                show_cta=item["show_cta"],
                display_order=index,
                is_active=True,
            ))

    db.session.commit()
