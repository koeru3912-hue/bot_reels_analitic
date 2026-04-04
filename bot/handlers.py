import logging
from telegram import Update
from telegram.ext import ContextTypes
from bot.telegram_bot import load_top_content
from generator.gemini import generate_scenario

logger = logging.getLogger(__name__)


async def handle_scenario_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает нажатие кнопки — генерирует сценарий через Gemini."""
    query = update.callback_query

    try:
        await query.answer("⏳ Генерирую сценарий...")
    except Exception as e:
        logger.warning(f"Не удалось ответить на callback: {e}")

    # Получаем индекс из callback_data: "scenario_0", "scenario_1", ...
    idx = int(query.data.split("_")[1])
    items = load_top_content()

    if idx >= len(items):
        await query.message.reply_text("⚠️ Данные устарели. Дождитесь нового отчёта.")
        return

    item = items[idx]
    scenario = generate_scenario(item)

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
