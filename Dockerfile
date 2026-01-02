FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY PhotoBridge_BE/requirements.txt /tmp/requirements.txt

RUN python -m pip install --upgrade pip \
    && python -m pip install -r /tmp/requirements.txt

COPY . /app/PhotoBridge_BE

RUN useradd --create-home --uid 1001 appuser \
    && chown -R appuser:appuser /app

USER appuser

ENV PYTHONPATH=/app \
    PORT=8000

EXPOSE 8000

CMD ["uvicorn", "PhotoBridge_BE.main:app", "--host", "0.0.0.0", "--port", "8000"]

