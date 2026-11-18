# Production Dockerfile for DEBUNK.IT
FROM python:3.12-slim

# Allow statements and log messages to immediately appear in logs
ENV PYTHONUNBUFFERED=True \
    PYTHONDONTWRITEBYTECODE=1 \
    FLASK_ENV=production \
    PORT=8080

# Install system dependencies (C-compiler for packages if needed, libpq for Postgres)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install production dependencies first (utilizes Docker layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Ensure runtime directories exist
RUN mkdir -p logs instance

EXPOSE 8080

# Run the web service using Gunicorn (binds to $PORT or default 8080)
CMD exec gunicorn --bind 0.0.0.0:${PORT:-8080} --workers 1 --threads 8 --timeout 60 debunkit_app:app
