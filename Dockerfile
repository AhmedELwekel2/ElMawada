FROM python:3.11-slim

# System deps for WeasyPrint / Cairo / Pango and Arabic fonts (magazine PDF render).
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        libpango-1.0-0 \
        libpangocairo-1.0-0 \
        libcairo2 \
        libgdk-pixbuf-2.0-0 \
        libffi8 \
        libjpeg62-turbo \
        zlib1g \
        fonts-dejavu-core \
        fonts-liberation \
        fonts-hosny-amiri \
        libxml2-dev \
        libxslt-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first (better layer caching).
COPY quality_bot/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# NLTK tokenizer data used by article content extraction.
RUN python -c "import nltk; nltk.download('punkt')"

# Playwright headless Chromium (renders the JS single-page gov sources) + its
# system libraries. Meaningfully increases image size.
RUN playwright install --with-deps chromium

# Copy the whole project: telegram_bot_family.py + templates/ + Amiri font live at
# the repo root, and the agent + API live under quality_bot/.
COPY . .

ENV PYTHONUNBUFFERED=1

# Run from quality_bot so .env and the Amiri font resolve correctly; the agent puts
# the repo root on sys.path to import telegram_bot_family.
WORKDIR /app/quality_bot

EXPOSE 8010

# Serve the FastAPI app. (To run the Telegram bot instead: python -m agent.bot)
CMD ["python", "-m", "uvicorn", "agent.api:app", "--host", "0.0.0.0", "--port", "8010"]
