import logging
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.telegram_bot import load_top_content
from generator.gemini import generate_scenario, generate_hooks_analysis
from analytics.history import get_history_summary
from analytics.channel_stats import get_weekly_report

logger = logging.getLogger(__name__)

MAIN_KEYBOARD = ReplyKeyboardMarkup(
    [
        ["🎬 Рилсы", "✍️ Написать пост"],
        ["📊 Аналитика", "🔍 Конкуренты"],
        ["💬 Комментинг"],
    ],
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


async def handle_hooks_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Анализ хуков на основе текущего топ-5."""
    query = update.callback_query

    try:
        await query.answer("⏳ Анализирую хуки...")
    except Exception:
        pass

    items = load_top_content()
    if not items:
        await query.message.reply_text("⚠️ Нет данных. Сначала нажмите 🎬 Рилсы.")
        return

    await query.message.reply_text("⏳ Анализирую паттерны хуков...")

    import asyncio
    analysis = await asyncio.get_event_loop().run_in_executor(
        None, generate_hooks_analysis, items
    )

    try:
        await query.message.reply_text(
            analysis,
            parse_mode="Markdown",
            disable_web_page_preview=True,
        )
    except Exception:
        await query.message.reply_text(analysis)


async def handle_reels_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает нажатие кнопки 'Рилсы'."""
    await update.message.reply_text("⏳ Собираю данные...")

    from main import daily_job
    await daily_job(context)



async def handle_analytics_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает меню аналитики."""
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📈 Еженедельный отчёт", callback_data="analytics_weekly"),
        ],
        [
            InlineKeyboardButton("📅 История топов", callback_data="analytics_history"),
        ],
    ])
    await update.message.reply_text(
        "📊 *Аналитика*\n\nВыберите отчёт:",
        reply_markup=keyboard,
        parse_mode="Markdown",
    )


async def handle_analytics_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает выбор в меню аналитики."""
    query = update.callback_query
    await query.answer()

    if query.data == "analytics_weekly":
        report = get_weekly_report()
        try:
            await query.message.edit_text(report, parse_mode="Markdown")
        except Exception:
            await query.message.edit_text(report)

    elif query.data == "analytics_history":
        summary = get_history_summary(days=7)
        try:
            await query.message.edit_text(summary, parse_mode="Markdown")
        except Exception:
            await query.message.edit_text(summary)


async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает команду /start."""
    await update.message.reply_text(
        "👋 Привет! Я AI-ассистент маркетолога.\n\n"
        "🎬 *Рилсы* — топ-5 идей + AI-сценарии\n"
        "✍️ *Написать пост* — пост из голосового\n"
        "📊 *Аналитика* — статистика и история\n"
        "🔍 *Конкуренты* — мониторинг каналов\n"
        "💬 *Комментинг* — AI-комментарии к постам\n\n"
        "Каждый день в 9:00 присылаю топ-5 идей для контента.",
        reply_markup=MAIN_KEYBOARD,
        parse_mode="Markdown",
    )
