"""Telegram layer for the LangGraph agent.

Responsibilities kept thin: usage gating, driving a compiled StateGraph with
``astream`` (editing the Telegram message live as nodes emit ``progress``), and
sending the resulting PDFs. The four LLM-driven report generators
(daily / weekly / monthly / magazine) run through the graphs; non-LLM features
(main menu, category browsing, keyword setup, usage/reset) delegate to the
original module's handlers so behaviour there is unchanged.

Run with:  ``python -m agent.bot``  (from the ``quality_bot`` directory)
"""
import logging
import os
from datetime import datetime

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from telegram.request import HTTPXRequest

from . import _legacy as L
from .graphs import daily_graph, magazine_graph, periodic_graph

logger = logging.getLogger(__name__)

# Reused, unchanged handlers from the original module.
legacy = L.legacy
start = legacy.start
help_command = legacy.help_command
show_categories = legacy.show_categories
keywords_command = legacy.keywords_command
reset_command = legacy.reset_command
usage_command = legacy.usage_command
handle_message = legacy.handle_message


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
async def _reply(update: Update, text: str):
    if update.callback_query:
        await update.callback_query.answer()
        return await update.callback_query.message.reply_text(text, parse_mode="Markdown")
    return await update.message.reply_text(text, parse_mode="Markdown")


_OUTPUT_META = {
    "daily": ("Family_Daily_Report", "📄 *التقرير اليومي للأسرة والمجتمع*"),
    "combined": ("Family_Comprehensive_Report", "📝 *التقرير الشامل للأسرة والمجتمع*\n💼 تحليل شامل لكافة التطورات والأخبار في شؤون الأسرة والمجتمع"),
    "magazine": ("Family_Society_Magazine", "📖 *مجلة الأسرة والمجتمع الشهرية*\n\nاستمتع بتقريرك الشهري!"),
}


async def _send_output(message, output: dict):
    path = output.get("path")
    if not path or not os.path.exists(path):
        logger.error("Output PDF missing for kind=%s path=%s", output.get("kind"), path)
        return
    prefix, caption = _OUTPUT_META.get(output.get("kind"), ("Report", "📄 التقرير"))
    fname = f"{prefix}_{datetime.now().strftime('%Y%m%d')}.pdf"
    try:
        with open(path, "rb") as fh:
            await message.reply_document(
                document=fh, filename=fname, caption=caption, parse_mode="Markdown"
            )
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


async def _run_report(update, context, graph, initial, usage_key, intro, menu_buttons):
    """Generic driver: usage gate → stream graph (live progress) → send PDFs."""
    user_id = L.get_user_id(update)
    has_limit, used = L.check_usage_limit(user_id, usage_key)
    if not has_limit:
        limit = L.USAGE_LIMITS.get(usage_key, 0)
        await _reply(
            update,
            f"❌ *تم الوصول إلى الحد الأقصى*\n\nلقد استخدمت جميع المحاولات المتاحة ({limit}/{limit}).",
        )
        return

    L.increment_usage(user_id, usage_key)
    message = await _reply(update, intro)

    last_progress = None
    final_state = None
    try:
        async for snapshot in graph.astream(initial, stream_mode="values"):
            final_state = snapshot
            progress = snapshot.get("progress")
            if progress and progress != last_progress:
                last_progress = progress
                try:
                    await message.edit_text(progress, parse_mode="Markdown")
                except Exception:
                    pass

        if not final_state or final_state.get("error"):
            err = (final_state or {}).get("error") or "حدث خطأ غير متوقع."
            await message.edit_text(f"❌ {err}")
            return

        outputs = final_state.get("outputs") or []
        if not outputs:
            await message.edit_text("❌ تعذّر إنشاء التقرير (لا توجد مخرجات).")
            return

        for output in outputs:
            await _send_output(message, output)

        await message.edit_text(
            "✅ *تم إنشاء التقرير بنجاح.*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(menu_buttons),
        )
    except Exception as e:
        logger.exception("Report generation failed (%s)", usage_key)
        try:
            await message.edit_text(f"❌ حدث خطأ أثناء إنشاء التقرير: {e}")
        except Exception:
            pass


_MAIN_MENU = [
    [InlineKeyboardButton("📰 الملخص اليومي", callback_data="get_news")],
    [InlineKeyboardButton("📊 الملخص الأسبوعي", callback_data="generate_weekly"),
     InlineKeyboardButton("📅 الملخص الشهري", callback_data="generate_monthly")],
    [InlineKeyboardButton("📰 المجلة", callback_data="generate_magazine")],
    [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="main_menu")],
]


# --------------------------------------------------------------------------- #
# Graph-driven handlers
# --------------------------------------------------------------------------- #
async def news_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _run_report(
        update, context, daily_graph,
        {"report_type": "daily", "category": None, "keywords": L.get_user_keywords(context)},
        "daily_news",
        "🌍 جارٍ تجهيز موجز أخبار الأسرة والمجتمع...\n📖 يتم الآن جمع الأخبار من المصادر الرسمية والدولية...\n⏳ يرجى الانتظار للحظات.",
        _MAIN_MENU,
    )


async def weekly_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _run_report(
        update, context, periodic_graph,
        {"report_type": "weekly", "time_period": "weekly", "keywords": L.get_user_keywords(context)},
        "weekly",
        "📝 جارٍ إعداد التقرير الأسبوعي الشامل للأسرة والمجتمع...\n📊 سيتم تحليل أخبار آخر 7 أيام\n⏰ قد يستغرق ذلك بضع دقائق.",
        _MAIN_MENU,
    )


async def monthly_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _run_report(
        update, context, periodic_graph,
        {"report_type": "monthly", "time_period": "monthly", "keywords": L.get_user_keywords(context)},
        "monthly",
        "📅 جارٍ إعداد التقرير الشهري الشامل للأسرة والمجتمع...\n⏰ قد يستغرق ذلك بضع دقائق.",
        _MAIN_MENU,
    )


async def magazine_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _run_report(
        update, context, magazine_graph,
        {"report_type": "magazine"},
        "magazine",
        "🎨 جارٍ إعداد مجلة الأسرة والمجتمع الشهرية...\n🔍 تحليل أخبار الأسرة والمجتمع...\n⏰ قد يستغرق ذلك بضع دقائق.",
        _MAIN_MENU,
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Route LLM report actions to the graphs; delegate everything else to legacy."""
    data = update.callback_query.data
    if data == "get_news":
        await news_report(update, context)
    elif data == "generate_weekly":
        await weekly_report(update, context)
    elif data == "generate_monthly":
        await monthly_report(update, context)
    elif data == "generate_magazine":
        await magazine_report(update, context)
    else:
        # main_menu, category browsing, pagination, on-demand pdf_* buttons, etc.
        await legacy.button_handler(update, context)


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #
def main():
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO,
        force=True,
    )
    request = HTTPXRequest(
        connect_timeout=30.0, read_timeout=60.0, write_timeout=60.0, pool_timeout=30.0
    )
    application = (
        Application.builder()
        .token(L.TELEGRAM_TOKEN)
        .request(request)
        .get_updates_request(request)
        .build()
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("news", news_report))
    application.add_handler(CommandHandler("categories", show_categories))
    application.add_handler(CommandHandler("weekly", weekly_report))
    application.add_handler(CommandHandler("monthly", monthly_report))
    application.add_handler(CommandHandler("magazine", magazine_report))
    application.add_handler(CommandHandler("keywords", keywords_command))
    application.add_handler(CommandHandler("setkeywords", keywords_command))
    application.add_handler(CommandHandler("reset", reset_command))
    application.add_handler(CommandHandler("usage", usage_command))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🌍 Starting LangGraph-powered Family & Society News Bot...")
    print("📱 Send /start to begin.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
