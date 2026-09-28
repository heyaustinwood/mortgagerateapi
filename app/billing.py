"""Stripe Checkout for signup, the Stripe billing portal for everything after."""

import json

import stripe
from flask import Blueprint, abort, current_app, redirect, render_template, request
from sqlalchemy.exc import IntegrityError

from . import db
from .models import ApiKey

bp = Blueprint("billing", __name__)

# past_due keeps the key working while Stripe retries the card.
ACTIVE_STATUSES = {"active", "trialing", "past_due"}


def _stripe():
    stripe.api_key = current_app.config["STRIPE_SECRET_KEY"]
    return stripe


def issue_key(session):
    """Return the customer's key, creating it the first time. `session` is a Checkout Session dict."""
    customer = session["customer"]
    api_key = ApiKey.query.filter_by(stripe_customer_id=customer).first()
    if api_key:
        return api_key
    details = session.get("customer_details") or {}
    api_key = ApiKey(
        key=ApiKey.new_key(),
        email=details.get("email"),
        stripe_customer_id=customer,
        stripe_subscription_id=session.get("subscription"),
        active=True,
    )
    db.session.add(api_key)
    try:
        db.session.commit()
    except IntegrityError:
        # The webhook and the welcome page raced; the other one won.
        db.session.rollback()
        api_key = ApiKey.query.filter_by(stripe_customer_id=customer).one()
    return api_key


@bp.post("/subscribe")
def subscribe():
    base = current_app.config["BASE_URL"]
    session = _stripe().checkout.Session.create(
        mode="subscription",
        line_items=[{"price": current_app.config["STRIPE_PRICE_ID"], "quantity": 1}],
        success_url=f"{base}/welcome?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{base}/#pricing",
        allow_promotion_codes=True,
    )
    return redirect(session.url, 303)


@bp.get("/welcome")
def welcome():
    session_id = request.args.get("session_id", "")
    if not session_id.startswith("cs_"):
        return redirect("/")
    try:
        session = _stripe().checkout.Session.retrieve(session_id).to_dict()
    except stripe.InvalidRequestError:
        abort(404)
    if session["status"] != "complete":
        return redirect("/#pricing")
    return render_template("welcome.html", api_key=issue_key(session))


@bp.post("/billing")
def billing_portal():
    api_key = ApiKey.query.filter_by(key=request.form.get("api_key", "").strip()).first()
    if api_key is None:
        return redirect("/?billing=notfound#billing")
    portal = _stripe().billing_portal.Session.create(
        customer=api_key.stripe_customer_id,
        return_url=current_app.config["BASE_URL"] + "/",
    )
    return redirect(portal.url, 303)


@bp.post("/stripe/webhook")
def webhook():
    payload = request.get_data(as_text=True)
    try:
        stripe.WebhookSignature.verify_header(
            payload,
            request.headers.get("Stripe-Signature", ""),
            current_app.config["STRIPE_WEBHOOK_SECRET"],
        )
    except stripe.SignatureVerificationError:
        abort(400)

    event = json.loads(payload)
    obj = event["data"]["object"]

    if event["type"] == "checkout.session.completed" and obj.get("mode") == "subscription":
        issue_key(obj)
    elif event["type"] in ("customer.subscription.updated", "customer.subscription.deleted"):
        api_key = ApiKey.query.filter_by(stripe_customer_id=obj["customer"]).first()
        if api_key:
            api_key.stripe_subscription_id = obj["id"]
            api_key.active = obj["status"] in ACTIVE_STATUSES
            db.session.commit()

    return "", 200
