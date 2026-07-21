"""FastAPI test harness for the Family & Society LangGraph agent.

Exposes the four report pipelines (daily / weekly / monthly / magazine) as HTTP
endpoints that drive the compiled graphs directly — bypassing Telegram and the
per-user usage limits — so you can verify the agent end to end.

Run with (from the ``quality_bot`` directory):

    uvicorn agent.api:app --reload --port 8000
    # or:  python -m agent.api

Then open http://127.0.0.1:8000/docs for an interactive UI.

Each endpoint runs the full pipeline (live scraping + LLM generation + PDF
render), so a request can take a few minutes. The ``format`` query param controls
the response:

* ``file`` (default) – save the PDF under ``generated/`` and return JSON with a
  ``download_url`` you can open directly in a browser. Easiest in Postman.
* ``pdf``            – stream the PDF binary as a file download.
* ``json``           – return the raw markdown / magazine JSON (no PDF kept).
"""
import asyncio
import logging
import os
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import Body, FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.background import BackgroundTask

from . import _legacy as L
from .graphs import daily_graph, magazine_graph, periodic_graph

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Directory where generated PDFs are saved (for ``format=file``) and served from.
GENERATED_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "generated")
os.makedirs(GENERATED_DIR, exist_ok=True)

app = FastAPI(
    title="Family & Society News Agent API",
    description="Test harness for the LangGraph-powered Family & Society report agent.",
    version="1.0.0",
)

# Allow browser-based frontends (any origin) to call the API during development.
# Tighten ``allow_origins`` to your real frontend URL(s) before production.
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Saved PDFs are downloadable at /files/<name>.pdf
app.mount("/files", StaticFiles(directory=GENERATED_DIR), name="files")


# --------------------------------------------------------------------------- #
# Request models
# --------------------------------------------------------------------------- #
class DailyRequest(BaseModel):
    category: Optional[str] = None          # e.g. "الأسرة والطفولة" | "الصحة والرفاهية"
    keywords: Optional[Dict[str, Any]] = None


class PeriodicRequest(BaseModel):
    keywords: Optional[Dict[str, Any]] = None


class MagazineRequest(BaseModel):
    keywords: Optional[Dict[str, Any]] = None


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _cleanup(path: str):
    try:
        if path and os.path.exists(path):
            os.unlink(path)
    except OSError:
        pass


async def _run(graph, initial: dict):
    """Invoke a compiled graph and return its final state (raising on error)."""
    final_state = await graph.ainvoke(initial)
    if not final_state or final_state.get("error"):
        err = (final_state or {}).get("error") or "حدث خطأ غير متوقع."
        raise HTTPException(status_code=502, detail=err)
    return final_state


def _pdf_response(state: dict, download_name: str) -> FileResponse:
    outputs = state.get("outputs") or []
    if not outputs:
        raise HTTPException(status_code=502, detail="تعذّر إنشاء التقرير (لا توجد مخرجات).")
    path = outputs[0].get("path")
    if not path or not os.path.exists(path):
        raise HTTPException(status_code=502, detail="ملف PDF غير موجود بعد التوليد.")
    return FileResponse(
        path,
        media_type="application/pdf",
        filename=download_name,
        background=BackgroundTask(_cleanup, path),
    )


def _json_response(state: dict) -> JSONResponse:
    """Return generated content + output metadata without streaming the PDF.

    The PDF (if any) is cleaned up since it won't be downloaded here.
    """
    payload = {
        "report_type": state.get("report_type"),
        "time_period": state.get("time_period"),
        "enhanced_count": state.get("enhanced_count"),
        "article_count": len(state.get("articles") or []),
        "blog_content": state.get("blog_content"),
        "combined_blog": state.get("combined_blog"),
        "magazine_data": state.get("magazine_data"),
        "outputs": [{"kind": o.get("kind")} for o in (state.get("outputs") or [])],
    }
    for o in state.get("outputs") or []:
        _cleanup(o.get("path"))
    return JSONResponse(content=payload)


def _file_response(state: dict, request: Request, download_name: str) -> JSONResponse:
    """Persist the PDF under ``generated/`` and return a browser-openable URL."""
    outputs = state.get("outputs") or []
    if not outputs:
        raise HTTPException(status_code=502, detail="تعذّر إنشاء التقرير (لا توجد مخرجات).")
    src = outputs[0].get("path")
    if not src or not os.path.exists(src):
        raise HTTPException(status_code=502, detail="ملف PDF غير موجود بعد التوليد.")

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    fname = f"{os.path.splitext(download_name)[0]}_{stamp}.pdf"
    dest = os.path.join(GENERATED_DIR, fname)
    os.replace(src, dest)

    download_url = str(request.base_url).rstrip("/") + f"/files/{fname}"
    return JSONResponse(content={
        "status": "ok",
        "report_type": state.get("report_type"),
        "time_period": state.get("time_period"),
        "article_count": len(state.get("articles") or []),
        "enhanced_count": state.get("enhanced_count"),
        "kind": outputs[0].get("kind"),
        "pdf_path": dest,
        "download_url": download_url,
    })


def _respond(state: dict, fmt: str, request: Request, download_name: str):
    if fmt == "json":
        return _json_response(state)
    if fmt == "pdf":
        return _pdf_response(state, download_name)
    return _file_response(state, request, download_name)


# --------------------------------------------------------------------------- #
# Endpoints
# --------------------------------------------------------------------------- #
@app.get("/health")
async def health():
    from . import config
    return {
        "status": "ok",
        "llm": {"bedrock": config.HAS_BEDROCK, "azure": config.HAS_AZURE},
        "model": config.BEDROCK_MODEL_ID,
    }


# --------------------------------------------------------------------------- #
# News listing (fast — fetch + filter only, no LLM, no PDF)
# --------------------------------------------------------------------------- #
def _normalize_article(a: dict) -> dict:
    src = a.get("source")
    src_name = src.get("name") if isinstance(src, dict) else (src or "")
    return {
        "title": a.get("title"),
        "source": src_name,
        "url": a.get("url"),
        "published_at": a.get("publishedAt") or a.get("published_at"),
        "description": a.get("description"),
        "image": a.get("urlToImage") or a.get("image_url") or a.get("image"),
    }


async def _news_listing(period: str, days: int, category: Optional[str], limit: int) -> dict:
    articles = await asyncio.to_thread(L.fetch_family_news) or []

    recent = await asyncio.to_thread(lambda: L.filter_recent_articles(articles, days=days) or [])
    if not recent:
        recent = articles  # fallback: show whatever was fetched

    # Narrow to the psychological family/society focus (keep recency set if empty).
    relevant = await asyncio.to_thread(lambda: L.filter_relevant_articles(recent) or [])
    recent = relevant or recent

    if category:
        cats = await asyncio.to_thread(L.categorize_articles, recent)
        recent = cats.get(category, [])

    items = [_normalize_article(a) for a in recent if a]
    items = items[:limit]
    return {
        "period": period,
        "days": days,
        "category": category,
        "count": len(items),
        "articles": items,
    }


@app.get("/news/daily", summary="List today's Family & Society news (no AI, no PDF)")
async def news_daily(
    days: int = Query(1, ge=1, le=365),
    category: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
):
    return await _news_listing("daily", days, category, limit)


@app.get("/news/weekly", summary="List this week's Family & Society news (no AI, no PDF)")
async def news_weekly(
    days: int = Query(7, ge=1, le=365),
    category: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=200),
):
    return await _news_listing("weekly", days, category, limit)


@app.get("/news/monthly", summary="List this month's Family & Society news (no AI, no PDF)")
async def news_monthly(
    days: int = Query(30, ge=1, le=365),
    category: Optional[str] = Query(None),
    limit: int = Query(150, ge=1, le=200),
):
    return await _news_listing("monthly", days, category, limit)


@app.post("/reports/daily", summary="Generate the daily Family & Society report")
async def daily(
    request: Request,
    body: Optional[DailyRequest] = Body(default=None),
    format: str = Query("file", pattern="^(file|pdf|json)$"),
):
    body = body or DailyRequest()
    state = await _run(daily_graph, {
        "report_type": "daily",
        "category": body.category,
        "keywords": body.keywords,
    })
    return _respond(state, format, request, "Family_Daily_Report.pdf")


@app.post("/reports/weekly", summary="Generate the weekly combined Family & Society report")
async def weekly(
    request: Request,
    body: Optional[PeriodicRequest] = Body(default=None),
    format: str = Query("file", pattern="^(file|pdf|json)$"),
):
    body = body or PeriodicRequest()
    state = await _run(periodic_graph, {
        "report_type": "weekly",
        "time_period": "weekly",
        "keywords": body.keywords,
    })
    return _respond(state, format, request, "Family_Weekly_Report.pdf")


@app.post("/reports/monthly", summary="Generate the monthly combined Family & Society report")
async def monthly(
    request: Request,
    body: Optional[PeriodicRequest] = Body(default=None),
    format: str = Query("file", pattern="^(file|pdf|json)$"),
):
    body = body or PeriodicRequest()
    state = await _run(periodic_graph, {
        "report_type": "monthly",
        "time_period": "monthly",
        "keywords": body.keywords,
    })
    return _respond(state, format, request, "Family_Monthly_Report.pdf")


@app.post("/reports/magazine", summary="Generate the monthly Family & Society magazine PDF")
async def magazine(
    request: Request,
    body: Optional[MagazineRequest] = Body(default=None),
    format: str = Query("file", pattern="^(file|pdf|json)$"),
):
    body = body or MagazineRequest()
    state = await _run(magazine_graph, {
        "report_type": "magazine",
        "keywords": body.keywords,
    })
    return _respond(state, format, request, "Family_Society_Magazine.pdf")


def main():
    import uvicorn
    uvicorn.run("agent.api:app", host="0.0.0.0", port=8000, reload=False)


if __name__ == "__main__":
    main()
