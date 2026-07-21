FROM python:3.11-slim

WORKDIR /app

# Install ALL system dependencies required by quality_bot (imported by backend):
# - WeasyPrint: cairo, pango, gdk-pixbuf, libffi, libjpeg, zlib
# - Playwright: needs its own install step below
# - Arabic PDF: fonts-hosny-amiri
# - BeautifulSoup/lxml: libxml2, libxslt
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        libpango-1.0-0 \
        libpangocairo-1.0-0 \
        libpangoft2-1.0-0 \
        libcairo2 \
        libgdk-pixbuf-2.0-0 \
        libffi8 \
        libjpeg62-turbo \
        zlib1g \
        fonts-dejavu-core \
        fonts-liberation \
        fonts-hosny-amiri \
        fontconfig \
        libxml2 \
        libxml2-dev \
        libxslt-dev \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Copy the quality_bot package (agent layer) since the backend imports from it
COPY quality_bot /app/quality_bot

# The Family & Society domain module lives at the repo root and is imported as a
# top-level module (PROJECT_ROOT=/app is on sys.path). Copy it plus its font and
# templates so PDF rendering and font registration resolve inside the image.
COPY telegram_bot_family.py /app/telegram_bot_family.py
COPY Amiri-Regular.ttf /app/Amiri-Regular.ttf
COPY templates /app/templates

# Copy the backend code
COPY quality_platform/backend /app/quality_platform/backend

# Install python packages (bot first — heavier, then backend)
RUN if [ -f /app/quality_bot/requirements.txt ]; then pip install --no-cache-dir -r /app/quality_bot/requirements.txt; fi
RUN pip install --no-cache-dir -r /app/quality_platform/backend/requirements.txt

# Install Playwright browsers (chromium) — needed by custom_scrapers
RUN playwright install --with-deps chromium || true

# Ensure NLTK data is available
RUN python -c "import nltk; nltk.download('punkt')" || true

WORKDIR /app/quality_platform/backend

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
