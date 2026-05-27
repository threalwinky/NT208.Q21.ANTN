FROM python:3.12-slim AS base

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libpq-dev \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Development stage: source is bind-mounted at runtime ─────────────────────
FROM base AS development
EXPOSE 8000

# ── Production stage: bake source into image ─────────────────────────────────
FROM base AS production
COPY . .
EXPOSE 8000
