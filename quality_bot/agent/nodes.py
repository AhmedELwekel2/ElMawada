"""Graph nodes.

Each node is an ``async`` function ``(state) -> partial_state``. Blocking
domain calls (scraping, content extraction, PDF rendering) run in a worker
thread via ``asyncio.to_thread`` so they never block the Telegram event loop;
LLM generation uses the async LangChain layer. Every node sets ``progress`` so
the Telegram layer can surface live status while streaming the graph.

The domain pipeline mirrors the Family & Society bot (``telegram_bot_family``):
sources are Twitter/X + RSS + gov/international sites (topically curated, so no
relevance filter — only recency), the periodic report is a single combined blog,
and the magazine back-fills article images from the original sources.
"""
import asyncio
import json
import logging
import re
from datetime import datetime

from . import llm, prompts
from . import _legacy as L
from .state import ReportState

logger = logging.getLogger(__name__)

# English SEO labels the model sometimes prepends before the Arabic report.
_SEO_MARKERS = (
    "SEO Title", "Meta Description", "Recommended Slug", "Headings Structure",
    "Slug:", "Meta:", "Title:", "SEO Metadata", "العناصر الإلزامية", "SEO العناصر",
)


def _strip_seo_preamble(text: str) -> str:
    """Remove a leading SEO metadata block (English labels) the model prepends
    before the actual Arabic content. Ported from the legacy quality module."""
    if not text:
        return text
    lines = text.split("\n")
    # Preferred: cut everything up to the first horizontal rule, if the block
    # above it looks like SEO metadata.
    for i, line in enumerate(lines):
        s = line.strip()
        if s in ("---", "***", "___") or (len(s) >= 3 and set(s) <= {"-", "=", "*", "_"}):
            preamble = "\n".join(lines[:i])
            if any(m in preamble for m in _SEO_MARKERS):
                logger.info("Stripped SEO preamble (%d lines)", i)
                return "\n".join(lines[i + 1:]).lstrip()
            break
    # Fallback: drop leading SEO-labeled / outline lines.
    cleaned, skipping = [], True
    for line in lines:
        s = line.strip()
        if skipping:
            if not s:
                continue
            if any(m in s for m in _SEO_MARKERS):
                continue
            if re.match(r"^[\-\*•]\s*H[1-6]\s*:", s):
                continue
            skipping = False
        cleaned.append(line)
    return "\n".join(cleaned).lstrip()


# --------------------------------------------------------------------------- #
# Fetch  (Twitter/X + RSS + gov/international sites)
# --------------------------------------------------------------------------- #
async def _fetch_family_sources():
    raw = await asyncio.to_thread(L.fetch_family_news)
    return raw or []


async def fetch_daily(state: ReportState) -> ReportState:
    raw = await _fetch_family_sources()
    logger.info("fetch_daily: %d articles", len(raw))
    return {
        "raw_articles": raw,
        "progress": "🌍 *الخطوة 1/4:* جلب الأخبار من المصادر الرسمية والدولية...",
    }


async def fetch_periodic(state: ReportState) -> ReportState:
    raw = await _fetch_family_sources()
    logger.info("fetch_periodic: %d articles", len(raw))
    return {
        "raw_articles": raw,
        "progress": "📝 *الخطوة 1/4:* جلب أخبار الأسرة والمجتمع من المصادر...",
    }


# --------------------------------------------------------------------------- #
# Filter (recency only — the sources are already topically curated)
# --------------------------------------------------------------------------- #
def _recency_filter(raw, days):
    recent = L.filter_recent_articles(raw, days=days) or []
    if not recent:
        logger.warning("No articles within %d days — falling back to full set", days)
        recent = (raw or [])[:30]
    # Order psych/family-relevant articles first so the enhancement budget
    # prioritizes them, but keep the rest as spillover — the post-enhancement
    # full-text pass (_focus, in enhance_*) re-checks each article's extracted
    # body, so items that are on-topic in the body but not the headline still
    # survive on days with few headline matches.
    relevant = L.filter_relevant_articles(recent) or []
    rel_ids = {id(a) for a in relevant}
    ordered = relevant + [a for a in recent if id(a) not in rel_ids]
    logger.info("filter: %d relevant-by-headline of %d recent (relevant-first)",
                len(relevant), len(ordered))
    return ordered


def _focus(enhanced):
    """Full-text relevance pass: keep only articles whose extracted body matches
    the psych/family focus. Falls back to the enhanced set if nothing matches so
    the pipeline still produces output."""
    focused = L.filter_relevant_articles(enhanced) or []
    if not focused:
        logger.warning("Full-text focus pass matched nothing — keeping enhanced set")
        return enhanced
    logger.info("focus pass: %d of %d enhanced articles on-topic", len(focused), len(enhanced))
    return focused


async def filter_articles(state: ReportState) -> ReportState:
    period = state.get("time_period")
    report_type = state.get("report_type", "daily")
    days = 30 if (period == "monthly" or report_type == "magazine") else 7
    articles = await asyncio.to_thread(
        _recency_filter, state.get("raw_articles") or [], days
    )
    logger.info("filter_articles: %d recent (<= %d days)", len(articles), days)
    return {
        "articles": articles,
        "progress": "🔍 *الخطوة 2/4:* تصفية أخبار الأسرة والمجتمع...",
    }


# --------------------------------------------------------------------------- #
# Enhance (full-content extraction)
# --------------------------------------------------------------------------- #
async def enhance_daily(state: ReportState) -> ReportState:
    articles = state.get("articles") or []
    enhanced = await asyncio.to_thread(
        L.enhance_articles_with_content, articles, 30
    )
    enhanced = _focus(enhanced or [])
    return {
        "articles": enhanced,
        "enhanced_count": sum(1 for a in enhanced if a.get("full_content")),
        "progress": "📖 *الخطوة 3/4:* استخراج المحتوى الكامل للمقالات...",
    }


async def enhance_periodic(state: ReportState) -> ReportState:
    articles = state.get("articles") or []
    weekly = state.get("time_period", "weekly") == "weekly"
    max_articles = 50 if weekly else 30
    enhanced = await asyncio.to_thread(
        lambda: L.enhance_articles_with_content(
            articles, max_articles=max_articles, weekly_mode=weekly, monthly_mode=not weekly
        )
    )
    enhanced = _focus(enhanced or [])
    return {
        "articles": enhanced,
        "enhanced_count": sum(1 for a in enhanced if a.get("full_content")),
        "progress": "📖 *الخطوة 3/4:* استخراج المحتوى الكامل للمقالات...",
    }


# --------------------------------------------------------------------------- #
# Generate
# --------------------------------------------------------------------------- #
async def generate_daily(state: ReportState) -> ReportState:
    articles = state.get("articles") or []
    if not articles:
        return {"error": "لا توجد مقالات متاحة اليوم."}
    system, user = prompts.daily_blog(articles, state.get("category"), state.get("keywords"))
    text, error = await llm.ainvoke_text(system, user, max_tokens=2200, temperature=0.45)
    if error or not text:
        logger.warning("generate_daily fell back: %s", error)
        text = L.build_fallback_family_blog_content(articles, state.get("category"))
    else:
        text = _strip_seo_preamble(text)
        if not text.lstrip().startswith("#"):
            text = "# التقرير اليومي للأسرة والمجتمع\n\n" + text
    return {
        "blog_content": text,
        "progress": "✍️ *الخطوة 4/4:* إنهاء إعداد التقرير...",
    }


async def generate_periodic(state: ReportState) -> ReportState:
    articles = state.get("articles") or []
    if not articles:
        return {"error": "لم يتم العثور على أخبار كافية عن الأسرة والمجتمع."}

    period = state.get("time_period", "weekly")
    system, user = prompts.periodic_blog(articles, "combined", period, state.get("keywords"))
    text, error = await llm.ainvoke_text(system, user, max_tokens=3500, temperature=0.5)
    if error or not text:
        logger.error("generate_periodic error: %s", error)
        return {"error": error or "تعذّر توليد التقرير."}
    return {
        "combined_blog": _strip_seo_preamble(text),
        "progress": "✍️ *الخطوة 4/4:* إنشاء التقرير وتنسيق الملف...",
    }


async def generate_magazine(state: ReportState) -> ReportState:
    articles = state.get("articles") or []
    if not articles:
        return {"error": "لا توجد مقالات كافية لإنشاء المجلة."}

    # Rebuild the article_index -> article map exactly as the prompt enumerates
    # the first 40 articles, so the model's article_index back-references resolve.
    article_map = {i + 1: art for i, art in enumerate(articles[:40])}

    system, user = prompts.magazine(articles)
    text, error = await llm.ainvoke_text(system, user, max_tokens=50000, temperature=0.7)
    if error or not text:
        return {"error": error or "تعذّر توليد محتوى المجلة."}

    data = _parse_magazine_json(text)
    if data is None:
        return {"error": "تعذّر تحليل محتوى المجلة (JSON غير صالح أو مقتطع)."}

    # Back-fill images/locations from the original articles (blocking: og:image scrape).
    await asyncio.to_thread(_backfill_magazine_images, data, article_map)
    data["date"] = datetime.now().strftime("%B %Y")

    return {
        "magazine_data": data,
        "progress": "🎨 *الخطوة 4/4:* تنسيق المجلة...",
    }


def _backfill_magazine_images(data: dict, article_map: dict):
    """Attach the correct source image to each magazine article via article_index,
    scraping og:image as a fallback — mirrors the magazine handler."""
    for mag_article in data.get("articles", []) or []:
        try:
            idx = int(mag_article.get("article_index"))
        except (TypeError, ValueError):
            idx = None
        orig = article_map.get(idx) if idx else None

        if orig and not mag_article.get("image_url"):
            img = (
                orig.get("urlToImage")
                or orig.get("image_url")
                or orig.get("image")
                or ""
            )
            if img:
                mag_article["image_url"] = img
            else:
                url = orig.get("url", "")
                if url:
                    try:
                        og_img = L.scrape_og_image(url)
                    except Exception:
                        og_img = None
                    if og_img:
                        mag_article["image_url"] = og_img

        if not mag_article.get("location"):
            mag_article["location"] = "السعودية"


def _parse_magazine_json(content_text: str):
    json_str = content_text.strip()
    if json_str.startswith("```json"):
        json_str = json_str[7:]
    if json_str.startswith("```"):
        json_str = json_str[3:]
    if json_str.endswith("```"):
        json_str = json_str[:-3]
    json_str = json_str.strip()
    if not json_str.endswith("}"):
        logger.warning("Magazine JSON appears truncated (model may have hit max_tokens)")
        return None
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        logger.error("Failed to decode magazine JSON: %s", e)
        return None


# --------------------------------------------------------------------------- #
# Render PDFs (pure — returns file paths; Telegram layer sends them)
# --------------------------------------------------------------------------- #
async def render_daily(state: ReportState) -> ReportState:
    content = state.get("blog_content")
    if not content:
        return {}
    path = await asyncio.to_thread(
        L.create_family_blog_pdf, content,
        "التقرير اليومي للأسرة والمجتمع", True,
    )
    return {"outputs": [{"path": path, "kind": "daily"}]}


async def render_periodic(state: ReportState) -> ReportState:
    content = state.get("combined_blog")
    if not content:
        return {"error": "تعذّر توليد التقرير (بيانات غير كافية)."}
    period = state.get("time_period", "weekly")
    adj = "الأسبوعي" if period == "weekly" else "الشهري"
    path = await asyncio.to_thread(
        L.create_family_blog_pdf, content,
        f"التقرير {adj} الشامل للأسرة والمجتمع", True,
    )
    return {"outputs": [{"path": path, "kind": "combined"}]}


async def render_magazine(state: ReportState) -> ReportState:
    data = state.get("magazine_data")
    if not data:
        return {}
    import tempfile
    out = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    out.close()
    path = await asyncio.to_thread(L.render_magazine_pdf, data, out.name)
    return {"outputs": [{"path": path or out.name, "kind": "magazine"}]}
