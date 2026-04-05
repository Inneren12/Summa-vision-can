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

# Dependencies cached in separate layer — only re-downloaded when pyproject.toml changes
COPY pyproject.toml .
RUN mkdir -p src && touch src/__init__.py && \
    pip install --no-cache-dir . && \
    rm -rf src/

# Layer 2: Full source + reinstall
COPY . .
RUN pip install --no-cache-dir .

# TODO (0-2 or later): Add entrypoint script that runs
# alembic upgrade head before starting uvicorn.
# For now, run migrations manually after deploy:
#   docker compose exec api alembic upgrade head

# --- Single worker (R9) ---
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--proxy-headers", "--forwarded-allow-ips=*"]

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

EXPOSE 8000
