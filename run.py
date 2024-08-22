import os
from dotenv import load_dotenv
from app import create_app, db
from app.models import MortgageRate
import csv
from datetime import datetime

# Load environment variables from .env file
load_dotenv()

app = create_app(os.getenv('FLASK_CONFIG') or 'default')

@app.cli.command("init-db")
def init_db():
    db.create_all()
    print("Database initialized.")

@app.cli.command("load-data")
def load_data():
    def parse_date(date_string):
        return datetime.strptime(date_string, '%Y-%m-%d').date()

    # Load 15-year mortgage data
    with open('MORTGAGE15US.csv', 'r') as f:
        reader = csv.reader(f)
        next(reader)  # Skip header
        for row in reader:
            if row[1] != '.':
                rate = MortgageRate(
                    date=parse_date(row[0]),
                    term=15,
                    rate=float(row[1])
                )
                db.session.add(rate)

    # Load 30-year mortgage data
    with open('MORTGAGE30US.csv', 'r') as f:
        reader = csv.reader(f)
        next(reader)  # Skip header
        for row in reader:
            if row[1] != '.':
                rate = MortgageRate(
                    date=parse_date(row[0]),
                    term=30,
                    rate=float(row[1])
                )
                db.session.add(rate)

    db.session.commit()
    print("Mortgage rate data loaded.")

if __name__ == '__main__':
    app.run()