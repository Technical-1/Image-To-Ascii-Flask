FROM python:3.12-slim

# System libraries required at runtime:
# - libcairo2: needed by cairosvg to rasterize SVG uploads
RUN apt-get update && apt-get install -y --no-install-recommends \
        libcairo2 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY . .

ENV FLASK_ENV=production

# Render injects $PORT at runtime; default to 10000 for local runs.
CMD ["sh", "-c", "gunicorn app:app --bind 0.0.0.0:${PORT:-10000} --workers 2"]
