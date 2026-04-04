import logging
import random
from telegram import Update
from telegram.ext import ContextTypes
from bot.telegram_bot import load_top_content
from generator.templates import (
    SCENARIO_TEMPLATE,
    HOOKS,
    PROBLEMS,
    SOLUTIONS,
    PROOFS,
    CTAS,
)

logger = logging.getLogger(__name__)


async def handle_scenario_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает нажатие кнопки — генерирует сценарий."""
    query = update.callback_query

    try:
        await query.answer()
    except Exception as e:
        logger.warning(f"Не удалось ответить на callback: {e}")

    # Получаем индекс из callback_data: "scenario_0", "scenario_1", ...
    idx = int(query.data.split("_")[1])
    items = load_top_content()

    if idx >= len(items):
        await query.message.reply_text("⚠️ Данные устарели. Дождитесь нового отчёта.")
        return

    item = items[idx]

    scenario = SCENARIO_TEMPLATE.format(
        number=idx + 1,
        title=item.get("title", "Без названия"),
        platform=item.get("platform", ""),
        url=item.get("url", "#"),
        views=item.get("views", 0),
        likes=item.get("likes", 0),
        comments=item.get("comments", 0),
        reposts=item.get("reposts", 0),
        hook=random.choice(HOOKS),
        problem=random.choice(PROBLEMS),
        solution=random.choice(SOLUTIONS),
        proof=random.choice(PROOFS),
        cta=random.choice(CTAS),
    )

    try:
        await query.message.reply_text(
            scenario,
            parse_mode="Markdown",
            disable_web_page_preview=True,
        )
    except Exception:
        # Если Markdown не парсится, отправляем без форматирования
        await query.message.reply_text(scenario)


async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает команду /start."""
    await update.message.reply_text(
        "👋 Привет! Я бот-аналитик Reels.\n\n"
        "Каждый день в 9:00 я присылаю топ-5 идей для контента.\n"
        "Нажмите на кнопку с номером — получите готовый сценарий."
    )
