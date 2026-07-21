# Family & Society News Agent (الأسرة والمجتمع)

An Arabic news agent for family & society topics. It scrapes news from Saudi & international sources
(X/Twitter via the Twitter API v2, RSS/Atom feeds, and gov/institutional sites — some JS-rendered via
Playwright), runs a LangGraph
pipeline to generate Modern Standard Arabic reports (daily / weekly / monthly blogs + a monthly
magazine), renders them to PDF, and exposes them two ways: a **FastAPI** HTTP API and a **Telegram**
bot.

## Quick start

Run everything from the `quality_bot/` directory (the working directory matters — see Gotchas).

```bash
cd quality_bot
pip install -r requirements.txt

# FastAPI app (interactive docs at http://127.0.0.1:8010/docs)
python -m uvicorn agent.api:app --port 8010

# Telegram bot
python -m agent.bot
```

Configure credentials in `quality_bot/.env` (copy from `.env.example`): `TELEGRAM_TOKEN`, the AWS
Bedrock keys (`AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` / `AWS_BEDROCK_INFERENCE_PROFILE_ID`),
the `TWITTER_BEARER_TOKEN`, and other keys. `.env` is gitignored.

### Docker

Build from the **repo root** (not `quality_bot/`), since the domain module and template assets live
there:

```bash
docker build -t family-bot .
./deploy_vps.sh        # builds + runs, passing secrets via --env-file
```

## API

Full endpoint reference for frontend developers is in [`quality_bot/API_README.md`](quality_bot/API_README.md).

- `GET /news/{daily,weekly,monthly}` — fast article listing (fetch + filter only, no LLM, ~2 s).
- `POST /reports/{daily,weekly,monthly,magazine}` — full LLM pipeline + PDF (1–6 min). The `format`
  query param returns a saved-PDF `download_url` (`file`, default), the raw PDF (`pdf`), or the text
  content (`json`).

## Architecture

The codebase is split across two locations, and the split is load-bearing:

- **`telegram_bot_family.py`** (repo root) — self-contained domain logic: the source registry +
  `fetch_family_news` (Twitter/X + RSS + static HTML + Playwright JS sites), recency filter,
  content extraction, categorization, ReportLab + WeasyPrint PDF rendering, usage limits, Arabic
  prompt/keyword helpers, and the Telegram command handlers. It imports no local modules.
- **`quality_bot/agent/`** — the LangGraph + FastAPI layer that orchestrates that logic.

`agent/_legacy.py` is the bridge: it puts the repo root on `sys.path`, imports `telegram_bot_family`,
and re-exports its functions under stable names. All domain calls in the agent go through `_legacy`
(aliased `L`).

### The pipeline (one StateGraph per report type)

`agent/graphs.py` compiles three graphs sharing the same shape:

```
fetch → filter → enhance → generate → (error? END : render) → END
```

`agent/nodes.py` implements each step; `agent/state.py` (`ReportState` TypedDict) threads state
through. Blocking domain calls run via `asyncio.to_thread`; LLM calls are async. Every node sets a
`progress` string the Telegram layer streams live.

- **daily** → one markdown blog (`blog_content`).
- **periodic** (weekly/monthly) → a single combined blog (`combined_blog`).
- **magazine** → magazine JSON (`magazine_data`); article images are back-filled via `article_index`
  (matching `articles[:40]`) with an og:image scrape fallback.

Daily/periodic generation strips the English SEO-metadata block the model sometimes prepends before
the Arabic report.

### LLM layer

`agent/llm.py` exposes `ainvoke_text(system, user) -> (text, error)`. Primary provider is AWS Bedrock
(`ChatBedrockConverse`); Azure Anthropic is the fallback. Prompts live in `agent/prompts.py`;
provider config in `agent/config.py` (read from env at import).

### Entry points

- `agent/api.py` — FastAPI (CORS open for dev; generated PDFs saved under `quality_bot/generated/`
  and served at `/files`).
- `agent/bot.py` — Telegram. Intercepts the four LLM actions to drive the graphs; delegates all
  other handlers (menu, categories, keywords, usage, pagination) to `telegram_bot_family` unchanged.

## Gotchas

- **Working directory matters.** `telegram_bot_family.py` registers the Amiri font with a CWD-relative
  path, so run from `quality_bot/` (which has `Amiri-Regular.ttf`). But it resolves `templates/`
  relative to its own file location (the repo root), so the templates and font also exist at the
  repo root. Both copies are intentional — keep them in sync.
- **Env-load ordering.** `telegram_bot_family` requires `AWS_BEARER_TOKEN_BEDROCK` at import, and
  `agent/config.py` reads env at import. `agent/__init__.py` calls `load_dotenv()` first so this
  works regardless of CWD or launcher (uvicorn). If `config.HAS_BEDROCK` is unexpectedly `False`,
  an import-ordering regression is the likely cause.

## Conventions

- All user-facing content is Modern Standard Arabic; report bodies are Markdown, magazine article
  `content` is HTML.
- Generated PDFs and runtime artifacts (`generated/`, `*_test.json`, `user_usage.json`) are gitignored.
