# Multi-platform production Dockerfile for DEBUNK.IT (Hugging Face Spaces, Cloud Run, Railway)
FROM python:3.12-slim

# Allow statements and log messages to immediately appear in logs
ENV PYTHONUNBUFFERED=True \
    PYTHONDONTWRITEBYTECODE=1 \
    FLASK_ENV=production \
    PORT=7860

# Install system dependencies (C-compiler for packages if needed, libpq for Postgres)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Hugging Face Spaces requires running as non-root user with UID 1000
RUN useradd -m -u 1000 user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

WORKDIR /home/user/app

# Install production dependencies first (utilizes Docker layer caching)
COPY --chown=user:user requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY --chown=user:user . .

# Ensure logs and app directory are fully writable
RUN mkdir -p logs instance && chown -R user:user /home/user/app

USER user

EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request, os; urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"PORT\", 7860)}/api/health')" || exit 1

# Run migrations and start web service with 60s timeout
CMD ["sh", "-c", "flask db upgrade && exec gunicorn --bind 0.0.0.0:${PORT:-7860} --workers 1 --threads 8 --timeout 60 debunkit_app:app"]
