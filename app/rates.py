"""Weekly mortgage rates from Freddie Mac's PMMS, published on FRED as free CSV."""

import csv
import io
import threading
import time
import urllib.request
from datetime import date

import click
from flask import current_app
from flask.cli import with_appcontext

from . import db
from .models import Rate

SERIES = {30: "MORTGAGE30US", 15: "MORTGAGE15US"}
FRED_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={}"


def fetch_series(series_id, attempts=3):
    # Keep urllib's default User-Agent: FRED's CDN drops some custom ones.
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(FRED_CSV.format(series_id), timeout=60) as resp:
                text = resp.read().decode("utf-8")
            break
        except OSError:
            if attempt == attempts - 1:
                raise
            time.sleep(5 * (attempt + 1))
    rows = csv.reader(io.StringIO(text))
    next(rows)  # header
    for day, value in rows:
        if value not in ("", "."):
            yield date.fromisoformat(day), float(value)


def sync():
    """Upsert every published reading. Returns how many rows were added or changed."""
    changed = 0
    for term, series_id in SERIES.items():
        existing = {r.date: r for r in Rate.query.filter_by(term=term)}
        for day, value in fetch_series(series_id):
            row = existing.get(day)
            if row is None:
                db.session.add(Rate(date=day, term=term, rate=value))
                changed += 1
            elif row.rate != value:
                row.rate = value
                changed += 1
    db.session.commit()
    return changed


@click.command("sync-rates")
@with_appcontext
def sync_command():
    """Pull the latest rates from FRED."""
    click.echo(f"Synced rates: {sync()} rows added or changed.")


def start_background_sync(app, every_seconds=6 * 3600):
    """Sync now, then every few hours. Freddie Mac publishes once a week (Thursdays)."""

    def loop():
        while True:
            with app.app_context():
                try:
                    current_app.logger.info("Rate sync: %s rows changed", sync())
                except Exception:
                    db.session.rollback()
                    current_app.logger.exception("Rate sync failed")
            time.sleep(every_seconds)

    threading.Thread(target=loop, daemon=True, name="rate-sync").start()
