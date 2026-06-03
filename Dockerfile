# ── Base image ─────────────────────────────────────────────────────────────
# Python 3.11 slim — small footprint, same as your Disney service images
FROM python:3.11-slim

# ── Labels (good practice — like your Disney image metadata) ───────────────
LABEL maintainer="Kranthi Vodnala"
LABEL project="ipl-score-predictor"
LABEL description="IPL Score Predictor — MLOps A/B Test Project 4"

# ── Environment variables ──────────────────────────────────────────────────
# These get overridden by docker-compose.yml per container
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    MODEL_STAGE=Production \
    MLFLOW_TRACKING_URI=http://mlflow:5000 \
    PORT=8000

# ── System dependencies ────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# libgomp1 = required by LightGBM (OpenMP for parallel trees)

# ── Working directory ──────────────────────────────────────────────────────
WORKDIR /app

# ── Install Python dependencies ────────────────────────────────────────────
# Copy requirements first — Docker layer caching
# If requirements.txt doesn't change, this layer is cached = faster builds
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ── Copy app code ──────────────────────────────────────────────────────────
COPY app/ .

# ── Health check ──────────────────────────────────────────────────────────
# Docker checks this every 30s — like your ECS health checks at Disney
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# ── Expose port ────────────────────────────────────────────────────────────
EXPOSE ${PORT}

# ── Start command ──────────────────────────────────────────────────────────
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT}