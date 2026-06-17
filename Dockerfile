FROM python:3.10-slim

WORKDIR /app

# System deps (psycopg2, numpy, TF often need these)
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (better caching)
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project
COPY . .

# Explicitly ensure models folder is included
COPY models /app/models

ENV PORT=8080

# Gunicorn + Flask app in main.py
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 main:app
