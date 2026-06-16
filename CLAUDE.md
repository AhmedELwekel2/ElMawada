# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A Hajj & Umrah Arabic news agent. It scrapes news (haj.gov.sa + CNN Arabic), runs a LangGraph
pipeline to generate Arabic reports (daily / weekly / monthly blogs + a monthly magazine), renders
them to PDF, and exposes them two ways: a **FastAPI** HTTP API and a **Telegram** bot.

## Commands

Run everything from the `quality_bot/` directory — see "Working directory matters" below.

```bash
cd quality_bot
pip install -r requirements.txt

# FastAPI app (interactive docs at http://127.0.0.1:8010/docs)
python -m uvicorn agent.api:app --port 8010

# Telegram bot
python -m agent.bot

# Docker (build from the REPO ROOT, not quality_bot/)
cd .. && docker build -t hajj-bot . && ./deploy_vps.sh
```

There is no test suite, linter, or build step configured. To smoke-test changes, import the package
(`python -c "import agent.api"`) and/or hit an endpoint. `GET /news/{daily,weekly,monthly}` is the
fast path (fetch + filter only, no LLM); `POST /reports/*` runs the full LLM pipeline (1–6 min).

## Architecture

The codebase is split across two locations, and the split is load-bearing:

- **`telegram_bot_hajj.py`** (repo root) — self-contained domain logic: scrapers, recency filter,
  content extraction, categorization, ReportLab + WeasyPrint PDF rendering, usage limits, Arabic
  prompt/keyword helpers, and the Telegram command handlers. It imports no local modules.
- **`quality_bot/agent/`** — the LangGraph + FastAPI layer that orchestrates that logic.

`agent/_legacy.py` is the bridge: it puts the repo root on `sys.path`, imports `telegram_bot_hajj`,
and re-exports its functions under stable names. **All domain calls in the agent go through
`_legacy` (aliased `L`)** — never import `telegram_bot_hajj` directly elsewhere.

### The pipeline (one StateGraph per report type)

`agent/graphs.py` compiles three graphs sharing the same shape:

```
fetch → filter → enhance → generate → (error? END : render) → END
```

`agent/nodes.py` implements each step; `agent/state.py` (`ReportState` TypedDict) threads state
through. Blocking domain calls run via `asyncio.to_thread`; LLM calls are async. Every node sets a
`progress` string the Telegram layer streams live.

- **daily** → `generate_daily` → one markdown blog (`blog_content`)
- **periodic** (weekly/monthly) → `generate_periodic` → a **single combined** blog (`combined_blog`).
  Note: this is one report, not two themed blogs.
- **magazine** → `generate_magazine` → magazine JSON (`magazine_data`), then images are back-filled
  per article via `article_index` (matching `articles[:40]`) with an og:image scrape fallback.

`generate_daily`/`generate_periodic` run `_strip_seo_preamble()` on the model output to drop the
English SEO metadata block the model sometimes prepends before the Arabic report.

### LLM layer

`agent/llm.py` exposes `ainvoke_text(system, user) -> (text, error)`. Primary provider is AWS
Bedrock (`ChatBedrockConverse`, model from `AWS_BEDROCK_INFERENCE_PROFILE_ID`); Azure Anthropic is
the fallback. Prompts live in `agent/prompts.py` (ported verbatim from the Hajj generation
functions). `agent/config.py` reads provider config from env at import time.

### Two entry points

- `agent/api.py` — FastAPI. `GET /news/*` (listing), `POST /reports/*` (full report). The `format`
  query param on report endpoints: `file` (default, saves PDF under `quality_bot/generated/` and
  returns a `download_url`), `pdf` (binary), `json` (text/JSON, no PDF). Has CORS open for dev.
- `agent/bot.py` — Telegram. Intercepts the four LLM actions (`get_news`, `generate_weekly`,
  `generate_monthly`, `generate_magazine`) to drive the graphs; delegates all other handlers
  (menu, categories, keywords, usage, pagination) to `telegram_bot_hajj` unchanged.

## Gotchas (verify these when things break)

- **Working directory matters.** `telegram_bot_hajj.py` registers the Amiri font with a CWD-relative
  path (`Amiri-Regular.ttf`), so run from `quality_bot/` (which has the font). But it resolves
  `templates/` relative to *its own file location* (the repo root), so the magazine/blog templates
  and font also exist at the repo root. Both copies are intentional — keep them in sync.
- **Env-load ordering.** `telegram_bot_hajj` requires `AWS_BEARER_TOKEN_BEDROCK` at import, and
  `agent/config.py` reads env at import. `agent/__init__.py` calls `load_dotenv()` on
  `quality_bot/.env` (and repo-root `.env`) first so this works regardless of CWD or launcher
  (uvicorn). If you add a new module that reads env at import, make sure `agent` is imported first.
- **Config defaults can mask credentials.** `config.HAS_BEDROCK` is `False` until `.env` is loaded;
  if Bedrock calls silently "have no credentials", an import ordering regression is the likely cause.

## Conventions

- All user-facing content is **Modern Standard Arabic**; English appears only in system prompts and
  source analysis. Report bodies are Markdown; magazine article `content` is HTML.
- `.env` holds real secrets and is gitignored — only `.env.example` is tracked.
- Generated PDFs and runtime artifacts (`generated/`, `*_test.json`, `user_usage.json`) are gitignored.
