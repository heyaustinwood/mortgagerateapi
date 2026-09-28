import os
from datetime import date

from dotenv import load_dotenv
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

load_dotenv()

db = SQLAlchemy()


def _database_url(app):
    url = os.environ.get("DATABASE_URL")
    if not url:
        return "sqlite:///" + os.path.join(app.instance_path, "rates.sqlite")
    # Hosts hand out postgres:// URLs; SQLAlchemy wants an explicit driver.
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix):]
    return url


def create_app(test_config=None):
    app = Flask(__name__)
    os.makedirs(app.instance_path, exist_ok=True)

    app.config.update(
        SQLALCHEMY_DATABASE_URI=_database_url(app),
        BASE_URL=os.environ.get("BASE_URL", "https://mortgagerateapi.com").rstrip("/"),
        STRIPE_SECRET_KEY=os.environ.get("STRIPE_SECRET_KEY", ""),
        STRIPE_PRICE_ID=os.environ.get("STRIPE_PRICE_ID", ""),
        STRIPE_WEBHOOK_SECRET=os.environ.get("STRIPE_WEBHOOK_SECRET", ""),
        PRICE_LABEL=os.environ.get("PRICE_LABEL", "$19/month"),
        SUPPORT_EMAIL=os.environ.get("SUPPORT_EMAIL", "support@mortgagerateapi.com"),
    )
    if test_config:
        app.config.update(test_config)

    app.json.sort_keys = False  # keep response fields in the documented order
    db.init_app(app)

    from . import api, billing, pages, rates

    app.register_blueprint(pages.bp)
    app.register_blueprint(api.bp)
    app.register_blueprint(billing.bp)
    app.cli.add_command(rates.sync_command)

    @app.context_processor
    def inject_year():
        return {"now_year": date.today().year}

    with app.app_context():
        db.create_all()

    if os.environ.get("SYNC_IN_BACKGROUND") == "1":
        rates.start_background_sync(app)

    return app
