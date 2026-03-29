FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_SYSTEM_PYTHON=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    ffmpeg \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

WORKDIR /workspace/backend

COPY backend/ /workspace/backend/

RUN uv pip install --system -e .[dev]

RUN useradd --create-home --shell /bin/bash appuser && \
    chown -R appuser:appuser /workspace/backend

USER appuser

EXPOSE 8000

