import os
import sys
import logging
import traceback
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import asyncio

from database import SessionLocal
from models import Article
from sqlalchemy import func
import re

# Ensure project root (.. ) is on sys.path so we can import quality_bot module
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(CURRENT_DIR))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

# Load credentials before importing the bot (see main.py for rationale).
from dotenv import load_dotenv  # noqa: E402
for _env in (
    os.path.join(CURRENT_DIR, ".env"),
    os.path.join(PROJECT_ROOT, "quality_platform", ".env"),
    os.path.join(PROJECT_ROOT, "quality_bot", ".env"),
    os.path.join(PROJECT_ROOT, ".env"),
):
    if os.path.exists(_env):
        load_dotenv(_env)

# Unset conflicting Bedrock tokens to prevent auth failures
os.environ.pop("AWS_BEARER_TOKEN_BEDROCK", None)

from telegram_bot_family import (  # type: ignore
    fetch_family_news,
    filter_relevant_articles,
    categorize_articles,
)

logger = logging.getLogger(__name__)


def _determine_category(article: dict) -> str:
    """Determine the Family & Society category for a single article.

    Reuses the bot's categorizer (categorize_articles) and returns the matching
    Arabic category label (one of FAMILY_CATEGORIES), defaulting to أخبار عامة.
    """
    buckets = categorize_articles([article]) or {}
    for cat, arts in buckets.items():
        if arts:
            return cat
    return 'أخبار عامة'


def fetch_and_store_news():
    """Fetch Family & Society news from all sources (Twitter/X + RSS + gov/international) and store in DB."""
    logger.info("Starting scheduled news fetch (Family & Society)...")
    db = SessionLocal()
    try:
        # fetch_family_news already aggregates Twitter + RSS + static HTML + JS
        # sources, merges, and de-duplicates.
        all_articles = fetch_family_news() or []
        logger.info(f"Fetched {len(all_articles)} articles from all Family & Society sources.")

        # Narrow to the psychological family/society focus.
        filtered = filter_relevant_articles(all_articles)
        logger.info(f"After relevance filtering: {len(filtered)} articles.")

        new_count = 0
        for article_data in filtered:
            url = article_data.get('url')
            if not url:
                continue

            # Check if already exists by URL
            existing = db.query(Article).filter(Article.url == url).first()
            # If no URL-match, try deduping by case-insensitive title + source
            if not existing:
                title = (article_data.get('title') or '').strip()
                source_obj = article_data.get('source')
                source_name = 'مجهول'
                if isinstance(source_obj, dict):
                    source_name = source_obj.get('name', 'مجهول')
                elif isinstance(source_obj, str):
                    source_name = source_obj

                if title:
                    try:
                        dup = db.query(Article).filter(
                            func.lower(Article.title) == title.lower(),
                            Article.source_name == source_name
                        ).first()
                    except Exception:
                        dup = None

                    if dup:
                        logger.info(f"Skipping duplicate article by title/source: {title[:60]} ({source_name}) -> existing id {dup.id}")
                        continue
            if not existing:
                try:
                    # Handle different date formats robustly
                    pub_str = article_data.get('publishedAt')
                    pub_dt = None
                    if pub_str:
                        pub_str = str(pub_str).strip()
                        try:
                            # 1. Try ISO format
                            if 'T' in pub_str:
                                try:
                                    pub_dt = datetime.fromisoformat(pub_str.replace('Z', '+00:00'))
                                    pub_dt = pub_dt.replace(tzinfo=None)
                                except:
                                    pass
                            
                            # 2. Try common human formats
                            if not pub_dt:
                                for fmt in ("%Y-%m-%d", "%d %b %Y", "%B %d, %Y", "%b %d, %Y", "%Y/%m/%d"):
                                    try:
                                        pub_dt = datetime.strptime(pub_str, fmt)
                                        break
                                    except:
                                        continue
                            
                            # 3. Last ditch attempt: slice first 10 chars for YYYY-MM-DD
                            if not pub_dt and len(pub_str) >= 10:
                                try:
                                    pub_dt = datetime.strptime(pub_str[:10], "%Y-%m-%d")
                                except:
                                    pass
                        except Exception:
                            pass

                    # source_name already computed above for dedupe (fallback if not set)
                    try:
                        source_name
                    except NameError:
                        source_obj = article_data.get('source')
                        source_name = "مجهول"
                        if isinstance(source_obj, dict):
                            source_name = source_obj.get('name', 'مجهول')
                        elif isinstance(source_obj, str):
                            source_name = source_obj

                    # Determine category using keyword scoring
                    category = _determine_category(article_data)

                    # Handle both 'content' and 'full_content'
                    content = article_data.get('content') or article_data.get('full_content', '')

                    new_article = Article(
                        title=article_data.get('title', ''),
                        description=article_data.get('description', ''),
                        url=url,
                        published_at=pub_dt,
                        source_name=source_name,
                        content=content,
                        category=category,
                        is_relevant=True,
                    )
                    db.add(new_article)
                    db.commit()
                    new_count += 1
                except Exception as e:
                    db.rollback()
                    logger.error(f"Error saving article {url}: {e}")

        logger.info(
            f"Finished scheduled fetch. Added {new_count} new articles "
            f"(Family & Society)."
        )
    finally:
        db.close()


def start_scheduler():
    scheduler = BackgroundScheduler()
    # Run every 1 day
    scheduler.add_job(
        fetch_and_store_news,
        trigger=IntervalTrigger(days=1),
        id="fetch_news_job",
        name="Fetch Family & Society news every 1 day",
        replace_existing=True,
        misfire_grace_time=3600,    # tolerate up to 1 hour delay before skipping
        coalesce=True,              # don't pile up missed runs
        max_instances=1,            # prevent overlapping runs
    )
    scheduler.start()

    # Log scheduler status for debugging
    job = scheduler.get_job("fetch_news_job")
    if job:
        logger.info(
            f"APScheduler started – news will be fetched every 1 day. "
            f"Next run at: {job.next_run_time}"
        )
    else:
        logger.warning("APScheduler started but job not found!")

    return scheduler
