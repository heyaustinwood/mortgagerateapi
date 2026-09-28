import hashlib
import hmac
import json
import time
from datetime import date

import pytest
import stripe

from app import create_app, db
from app.models import ApiKey, Rate

WEBHOOK_SECRET = "whsec_test"


@pytest.fixture
def app():
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite://",
        "STRIPE_WEBHOOK_SECRET": WEBHOOK_SECRET,
    })
    with app.app_context():
        db.create_all()
        db.session.add_all([
            Rate(date=date(2024, 1, 4), term=30, rate=6.62),
            Rate(date=date(2024, 1, 11), term=30, rate=6.66),
            Rate(date=date(2024, 2, 1), term=30, rate=6.63),
            Rate(date=date(2024, 1, 4), term=15, rate=5.89),
            ApiKey(key="mra_good", stripe_customer_id="cus_1", active=True),
            ApiKey(key="mra_lapsed", stripe_customer_id="cus_2", active=False),
        ])
        db.session.commit()
        yield app


@pytest.fixture
def client(app):
    return app.test_client()


def auth(key="mra_good"):
    return {"Authorization": f"Bearer {key}"}


def test_home_page_shows_latest_rate(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"6.63%" in resp.data


def test_rates_over_a_period(client):
    resp = client.get("/v1/rates?term=30&start=2024-01-01&end=2024-01-31", headers=auth())
    assert resp.status_code == 200
    assert resp.json["rates"] == [
        {"date": "2024-01-04", "rate": 6.62},
        {"date": "2024-01-11", "rate": 6.66},
    ]


def test_query_string_key_and_15_year(client):
    resp = client.get("/v1/rates?term=15&start=2024-01-01&end=2024-12-31&api_key=mra_good")
    assert resp.json["rates"] == [{"date": "2024-01-04", "rate": 5.89}]


def test_latest(client):
    resp = client.get("/v1/rates/latest", headers=auth())
    assert resp.json["rates"] == [
        {"term": 30, "date": "2024-02-01", "rate": 6.63},
        {"term": 15, "date": "2024-01-04", "rate": 5.89},
    ]


@pytest.mark.parametrize("headers,status,code", [
    ({}, 401, "missing_key"),
    (auth("mra_nope"), 401, "invalid_key"),
    (auth("mra_lapsed"), 402, "subscription_inactive"),
])
def test_auth_errors(client, headers, status, code):
    resp = client.get("/v1/rates", headers=headers)
    assert resp.status_code == status
    assert resp.json["error"]["code"] == code


@pytest.mark.parametrize("qs,code", [
    ("term=20", "invalid_term"),
    ("start=2024-13-01", "invalid_date"),
    ("start=2024-02-01&end=2024-01-01", "invalid_range"),
])
def test_bad_input(client, qs, code):
    resp = client.get(f"/v1/rates?{qs}", headers=auth())
    assert resp.status_code == 400
    assert resp.json["error"]["code"] == code


def post_webhook(client, event):
    payload = json.dumps(event)
    ts = int(time.time())
    sig = hmac.new(WEBHOOK_SECRET.encode(), f"{ts}.{payload}".encode(), hashlib.sha256).hexdigest()
    return client.post("/stripe/webhook", data=payload, headers={"Stripe-Signature": f"t={ts},v1={sig}"})


def test_webhook_rejects_bad_signature(client):
    resp = client.post("/stripe/webhook", data="{}", headers={"Stripe-Signature": "t=1,v1=bad"})
    assert resp.status_code == 400


def test_webhook_lifecycle(client, app):
    checkout = {"type": "checkout.session.completed", "data": {"object": {
        "mode": "subscription", "customer": "cus_new", "subscription": "sub_new",
        "customer_details": {"email": "a@example.com"},
    }}}
    assert post_webhook(client, checkout).status_code == 200
    assert post_webhook(client, checkout).status_code == 200  # Stripe retries are harmless
    with app.app_context():
        key = ApiKey.query.filter_by(stripe_customer_id="cus_new").one()
        assert key.active and key.email == "a@example.com"
        secret = key.key

    cancel = {"type": "customer.subscription.deleted", "data": {"object": {
        "id": "sub_new", "customer": "cus_new", "status": "canceled",
    }}}
    post_webhook(client, cancel)
    assert client.get("/v1/rates", headers=auth(secret)).status_code == 402


def test_welcome_shows_key(client, monkeypatch):
    session = stripe.checkout.Session.construct_from({
        "id": "cs_1", "status": "complete", "customer": "cus_1", "subscription": "sub_1",
        "customer_details": None,
    }, "sk")
    monkeypatch.setattr(stripe.checkout.Session, "retrieve", lambda sid: session)
    resp = client.get("/welcome?session_id=cs_1")
    assert resp.status_code == 200
    assert b"mra_good" in resp.data
