FROM python:3.11-slim

# --- System dependencies for CairoSVG, Pango, fonts, health checks ---
RUN apt-get update && apt-get install -y --no-install-recommends \
    libcairo2 libcairo2-dev \
    libpango-1.0-0 libpangocairo-1.0-0 \
    fonts-noto fonts-noto-cjk fonts-liberation \
    curl \
    && rm -rf /var/lib/apt/lists/*

# --- Polars CPU guard (R5) ---
ENV POLARS_MAX_THREADS=2

WORKDIR /app

# --- Install Python deps first (layer cache) ---
COPY pyproject.toml .
COPY . .
RUN pip install --no-cache-dir -e ".[dev]"

# --- Alembic migrations run before app start ---
# In production, run: alembic upgrade head && uvicorn ...
# For simplicity, CMD only starts uvicorn. Migrations in entrypoint or CI.

# --- Single worker (R9) ---
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--proxy-headers", "--forwarded-allow-ips=*"]

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

EXPOSE 8000
