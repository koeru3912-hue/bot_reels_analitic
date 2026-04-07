#!/usr/bin/env python3
"""Тест отправки сообщения + обработки кнопок в Telegram.
Использует реальный YouTube API для получения настоящих видео."""

import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent / ".env")

from telegram.ext import Application, CallbackQueryHandler, CommandHandler
from bot.telegram_bot import save_top_content, send_top_message
from bot.handlers import handle_scenario_button, handle_start
from config.settings import TELEGRAM_BOT_TOKEN
from parsers.youtube import fetch_youtube_shorts
from analytics.scorer import rank_content

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)


async def post_init(app: Application):
    """Собираем реальные видео с YouTube и отправляем топ-5."""
    print("📡 Собираю реальные видео с YouTube...")

    content = fetch_youtube_shorts()

    if not content:
        print("❌ Не удалось получить видео. Проверь YOUTUBE_API_KEY в .env")
        return

    ranked = rank_content(content)
    top = ranked[:5]

    print(f"✅ Найдено {len(content)} видео, отправляю топ-5")
    for i, item in enumerate(top, 1):
        print(f"   {i}. {item['title'][:60]}... → {item['url']}")

    save_top_content(top)
    await send_top_message(app)
    print("\n✅ Сообщение отправлено! Нажми кнопку в Telegram.")


def main():
    print("📤 Запускаю бота...")
    print("   Нажми кнопку в Telegram — получишь сценарий")
    print("   Ctrl+C — остановка")
    print()

    app = (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN)
        .connect_timeout(30)
        .read_timeout(30)
        .write_timeout(30)
        .build()
    )

    app.add_handler(CommandHandler("start", handle_start))
    app.add_handler(CallbackQueryHandler(handle_scenario_button, pattern=r"^scenario_\d+$"))

    app.post_init = post_init
    app.run_polling()


if __name__ == "__main__":
    main()
