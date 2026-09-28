import secrets
from datetime import datetime, timezone

from . import db


class Rate(db.Model):
    """One weekly Freddie Mac PMMS reading for one loan term."""

    __tablename__ = "rates"

    date = db.Column(db.Date, primary_key=True)
    term = db.Column(db.Integer, primary_key=True)
    rate = db.Column(db.Float, nullable=False)


class ApiKey(db.Model):
    """One key per Stripe customer. Active while their subscription is."""

    __tablename__ = "api_keys"

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(255))
    stripe_customer_id = db.Column(db.String(64), unique=True, nullable=False)
    stripe_subscription_id = db.Column(db.String(64))
    active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    @staticmethod
    def new_key():
        return "mra_" + secrets.token_urlsafe(24)
