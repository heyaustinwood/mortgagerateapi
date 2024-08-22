from .database import db
from datetime import datetime, timedelta
import secrets

class MortgageRate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    term = db.Column(db.Integer, nullable=False)
    rate = db.Column(db.Float, nullable=False)

    __table_args__ = (db.UniqueConstraint('date', 'term', name='_date_term_uc'),)

class Token(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(64), unique=True, nullable=False)
    expiry = db.Column(db.DateTime, nullable=False)

    @staticmethod
    def generate_token():
        token = Token(
            token=secrets.token_urlsafe(32),
            expiry=datetime.utcnow() + timedelta(days=30)
        )
        db.session.add(token)
        db.session.commit()
        return token