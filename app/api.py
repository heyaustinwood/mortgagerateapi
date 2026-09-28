from datetime import date, timedelta

from flask import Blueprint, jsonify, request

from .models import ApiKey, Rate

bp = Blueprint("api", __name__, url_prefix="/v1")

SOURCE = "Freddie Mac Primary Mortgage Market Survey (PMMS), via FRED"


class ApiError(Exception):
    def __init__(self, status, code, message):
        self.status, self.code, self.message = status, code, message


@bp.errorhandler(ApiError)
def handle_api_error(e):
    return jsonify(error={"code": e.code, "message": e.message}), e.status


@bp.before_request
def require_key():
    header = request.headers.get("Authorization", "")
    key = header[7:].strip() if header.lower().startswith("bearer ") else request.args.get("api_key", "")
    if not key:
        raise ApiError(401, "missing_key", "Send your key as 'Authorization: Bearer <key>'.")
    api_key = ApiKey.query.filter_by(key=key).first()
    if api_key is None:
        raise ApiError(401, "invalid_key", "That API key does not exist.")
    if not api_key.active:
        raise ApiError(402, "subscription_inactive", "This key's subscription is not active.")


def _term():
    term = request.args.get("term", "30")
    if term not in ("15", "30"):
        raise ApiError(400, "invalid_term", "term must be 15 or 30.")
    return int(term)


def _date(name, default):
    value = request.args.get(name)
    if not value:
        return default
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise ApiError(400, "invalid_date", f"{name} must be a date like 2024-01-31.")


@bp.get("/rates")
def rates():
    term = _term()
    end = _date("end", date.today())
    start = _date("start", end - timedelta(days=365))
    if start > end:
        raise ApiError(400, "invalid_range", "start must be on or before end.")

    rows = (
        Rate.query.filter(Rate.term == term, Rate.date >= start, Rate.date <= end)
        .order_by(Rate.date)
        .all()
    )
    return jsonify(
        term=term,
        start=start.isoformat(),
        end=end.isoformat(),
        source=SOURCE,
        rates=[{"date": r.date.isoformat(), "rate": r.rate} for r in rows],
    )


@bp.get("/rates/latest")
def latest():
    out = []
    for term in (30, 15):
        row = Rate.query.filter_by(term=term).order_by(Rate.date.desc()).first()
        if row:
            out.append({"term": term, "date": row.date.isoformat(), "rate": row.rate})
    return jsonify(source=SOURCE, rates=out)
