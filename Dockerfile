FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

ENV SYNC_IN_BACKGROUND=1 PORT=8000
# SQLite lives in /app/instance: mount a persistent volume there, or set DATABASE_URL.
VOLUME /app/instance

# One worker so the background rate sync runs once; threads handle concurrency.
CMD gunicorn --workers 1 --threads 8 --bind 0.0.0.0:$PORT run:app
