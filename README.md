# Mortgage Rate API

Weekly US mortgage rates (30-year and 15-year fixed) for any date range, as JSON.
Paid by subscription through Stripe. Runs at **mortgagerateapi.com**.

- **Data:** Freddie Mac PMMS, pulled from FRED (`MORTGAGE30US`, `MORTGAGE15US`), back to 1971. Free and needs no key.
- **API:** `GET /v1/rates?term=30&start=2024-01-01&end=2024-12-31` and `GET /v1/rates/latest`, with `Authorization: Bearer <key>`.
- **Billing:** one Stripe subscription. Checkout issues the key; the Stripe portal handles card changes and cancellation; a webhook switches the key off when a subscription ends.

The whole app is one small Flask package:

| File | What it does |
| --- | --- |
| `app/api.py` | The two `/v1` endpoints and key checks |
| `app/billing.py` | `/subscribe`, `/welcome`, `/billing`, `/stripe/webhook` |
| `app/rates.py` | Pulls rates from FRED (`flask sync-rates`, or in the background) |
| `app/pages.py`, `app/templates/` | The one-page docs and pricing site |

## Run it locally

```
python -m venv venv && source venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env          # fill in Stripe test keys
flask --app run sync-rates    # load ~4,700 weekly rates
flask --app run run           # http://127.0.0.1:5000
pytest
```

To test checkout end to end locally, forward webhooks with the Stripe CLI:
`stripe listen --forward-to localhost:5000/stripe/webhook` and put the `whsec_...` it prints in `.env`.

## Launch checklist

1. **Stripe.** Create a product with a recurring price (e.g. $19/month) and copy its `price_...` ID.
   In *Settings → Billing → Customer portal*, turn on "cancel subscription" and "update payment method".
   Add a webhook endpoint at `https://mortgagerateapi.com/stripe/webhook` for
   `checkout.session.completed`, `customer.subscription.updated` and `customer.subscription.deleted`; copy its signing secret.
2. **Host.** Any Docker host works (Render, Railway, Fly.io). Deploy this repo with the `Dockerfile` and set:
   `BASE_URL=https://mortgagerateapi.com`, `STRIPE_SECRET_KEY`, `STRIPE_PRICE_ID`, `STRIPE_WEBHOOK_SECRET`, `PRICE_LABEL`, `SUPPORT_EMAIL`.
   **Keys live in the database, so it must persist:** either attach a volume at `/app/instance` (SQLite)
   or set `DATABASE_URL` to a Postgres database. Health check path: `/healthz`.
3. **Domain.** Add `mortgagerateapi.com` (and `www`) as a custom domain on the host, then point DNS at it
   with the records the host gives you. The host issues the HTTPS certificate.
4. **Smoke test** with Stripe test keys first: subscribe with card `4242 4242 4242 4242`, call the API with the key
   you get, cancel in the billing portal, and check the key now returns `402`. Then swap in live keys.

The container pulls fresh rates on start and every 6 hours (`SYNC_IN_BACKGROUND=1`). Freddie Mac publishes on Thursdays.
