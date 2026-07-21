"""Shared graph state for all report workflows."""
from typing import Any, Dict, List, Optional, TypedDict


class ReportState(TypedDict, total=False):
    # --- inputs ---
    report_type: str                 # "daily" | "weekly" | "monthly" | "magazine"
    time_period: str                 # "weekly" | "monthly" (for periodic blogs)
    category: Optional[str]          # daily category filter
    keywords: Optional[Dict[str, Any]]

    # --- pipeline data ---
    raw_articles: List[dict]
    articles: List[dict]             # filtered + content-enhanced

    # --- generated content ---
    blog_content: str                # daily markdown
    combined_blog: Optional[str]     # weekly/monthly: single combined Family & Society report
    magazine_data: Optional[dict]    # magazine JSON

    # --- outputs ---
    outputs: List[dict]              # [{"path", "title", "kind"}]
    enhanced_count: int

    # --- control ---
    progress: str                    # latest human-readable step (streamed to Telegram)
    error: Optional[str]
