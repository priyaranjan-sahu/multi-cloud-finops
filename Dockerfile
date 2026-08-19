# Multi-stage production Dockerfile for Multi-Cloud FinOps Engine.
# Stage 1 compiles/installs dependencies, Stage 2 runs as a non-root user.

FROM python:3.10-slim AS builder

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# --- Runtime stage -----------------------------------------------------------
FROM python:3.10-slim AS runtime

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN groupadd --system finops && useradd --system --gid finops finops

COPY --from=builder /install /usr/local
COPY . .

RUN chown -R finops:finops /app
USER finops

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/', timeout=3)"

CMD ["uvicorn", "finops_engine.api.app:app", "--host", "0.0.0.0", "--port", "8000"]