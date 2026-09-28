from flask import Blueprint, render_template

from .models import Rate

bp = Blueprint("pages", __name__)


@bp.get("/")
def index():
    latest = {}
    for term in (30, 15):
        latest[term] = Rate.query.filter_by(term=term).order_by(Rate.date.desc()).first()
    first = Rate.query.order_by(Rate.date).first()
    return render_template("index.html", latest=latest, first=first)


@bp.get("/healthz")
def healthz():
    return {"ok": True}
