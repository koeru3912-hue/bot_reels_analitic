import json
import logging
from pathlib import Path
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)
from config.settings import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

logger = logging.getLogger(__name__)

DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "top_content.json"


def save_top_content(items: list[dict]):
    """Сохраняет топ-контент в файл для обработки кнопок."""
    DATA_FILE.parent.mkdir(exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)


def load_top_content() -> list[dict]:
    """Загружает сохранённый топ-контент."""
    if not DATA_FILE.exists():
        return []
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def build_top_message(items: list[dict]) -> tuple[str, InlineKeyboardMarkup]:
    """
    Формирует сообщение с топ-5 заголовками и инлайн-кнопками.
    """
    lines = ["🔥 *Топ-5 идей для Reels на сегодня*\n"]

    for i, item in enumerate(items, 1):
        title = item.get("title", "Без названия")
        url = item.get("url", "#")
        platform = item.get("platform", "")
        views = item.get("views", 0)
        likes = item.get("likes", 0)

        lines.append(
            f"*{i}.* [{title}]({url})\n"
            f"    _{platform}_ | 👁 {views:,} | ❤️ {likes:,}\n"
        )

    lines.append("\n👇 *Нажмите кнопку, чтобы получить сценарий:*")

    text = "\n".join(lines)

    # Создаём инлайн-кнопки: номера для сценариев + анализ хуков
    buttons = [
        InlineKeyboardButton(str(i), callback_data=f"scenario_{i-1}")
        for i in range(1, len(items) + 1)
    ]
    keyboard = InlineKeyboardMarkup([
        buttons,
        [InlineKeyboardButton("🎣 Анализ хуков", callback_data="hooks_analysis")],
    ])

    return text, keyboard


async def send_top_message(app: Application):
    """Отправляет сообщение с топ-5 в Telegram."""
    items = load_top_content()
    if not items:
        await app.bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text="⚠️ Нет данных для отправки. Проверьте парсеры.",
        )
        return

    text, keyboard = build_top_message(items)

    await app.bot.send_message(
        chat_id=TELEGRAM_CHAT_ID,
        text=text,
        parse_mode="Markdown",
        reply_markup=keyboard,
        disable_web_page_preview=True,
    )
    logger.info("Топ-5 отправлен в Telegram")
