import logging
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes
from bot.telegram_bot import load_top_content
from generator.gemini import generate_scenario

logger = logging.getLogger(__name__)

MAIN_KEYBOARD = ReplyKeyboardMarkup(
    [["🎬 Рилсы", "📤 Разместить"]],
    resize_keyboard=True,
)


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


async def handle_reels_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает нажатие кнопки 'Рилсы'."""
    await update.message.reply_text("⏳ Собираю данные...")

    from main import daily_job
    await daily_job(context)


async def handle_publish_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает нажатие кнопки 'Разместить'."""
    await update.message.reply_text(
        "📤 *Публикация видео*\n\n"
        "Отправьте мне видео (до 20 МБ), и я:\n"
        "1. Сгенерирую субтитры (SRT)\n"
        "2. Опубликую на Instagram, VK и YouTube\n\n"
        "Просто отправьте видеофайл прямо сюда:",
        parse_mode="Markdown",
    )


async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает команду /start."""
    await update.message.reply_text(
        "👋 Привет! Я бот-аналитик Reels.\n\n"
        "Каждый день в 9:00 я присылаю топ-5 идей для контента.\n"
        "🎬 *Рилсы* — получить топ-5 идей и сценарии\n"
        "📤 *Разместить* — загрузить видео и опубликовать на все площадки\n\n"
        "Отправьте видео напрямую — я добавлю субтитры и опубликую!",
        reply_markup=MAIN_KEYBOARD,
        parse_mode="Markdown",
    )
