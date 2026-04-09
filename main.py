#!/usr/bin/env python3
"""
Бот-аналитик Reels
Собирает топ контент с YouTube,
отправляет топ-5 заголовков в Telegram с кнопками.
По нажатию кнопки — генерирует сценарий.
"""

import sys
import os
import logging
from pathlib import Path
from datetime import time

from dotenv import load_dotenv

# Загружаем .env ДО импорта модулей
PROJECT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_DIR))
load_dotenv(PROJECT_DIR / ".env")

from telegram.ext import Application, CallbackQueryHandler, CommandHandler, MessageHandler, filters

from parsers.youtube import fetch_youtube_shorts
from analytics.scorer import rank_content
from bot.telegram_bot import save_top_content, send_top_message
from bot.handlers import (
    handle_scenario_button, handle_start, handle_reels_button,
    handle_analytics_button, handle_analytics_callback,
    handle_hooks_button,
)
from bot.post_handler import get_post_conversation_handler
from bot.competitor_handler import get_competitor_conversation_handler
from bot.commenting_handler import get_commenting_conversation_handler
from analytics.history import deduplicate, save_daily_top
from config.settings import TELEGRAM_BOT_TOKEN, TOP_COUNT

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def daily_job(context):
    """Ежедневная задача: сбор данных и отправка топ-5."""
    logger.info("Запуск ежедневного сбора данных...")

    all_content = fetch_youtube_shorts()

    if not all_content:
        logger.warning("Не удалось собрать контент")
        await context.bot.send_message(
            chat_id=os.getenv("TELEGRAM_CHAT_ID"),
            text="⚠️ Не удалось собрать данные. Проверьте API ключи.",
        )
        return

    ranked = rank_content(all_content)
    ranked = deduplicate(ranked)
    top = ranked[:TOP_COUNT]

    save_top_content(top)
    save_daily_top(top)
    await send_top_message(context.application)

    logger.info(f"Топ-{TOP_COUNT} отправлен")


async def cmd_collect(update, context):
    """Команда /collect — ручной запуск сбора данных."""
    await update.message.reply_text("⏳ Собираю данные...")
    await daily_job(context)


def main():
    print("=" * 50)
    print("🚀 Бот-аналитик Reels запущен")
    print("   Ежедневная отправка в 9:00")
    print("   /collect — ручной запуск")
    print("   ✍️ Написать пост — пост из голосового")
    print("   Ctrl+C — остановка")
    print("=" * 50)

    app = (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN)
        .connect_timeout(30)
        .read_timeout(30)
        .write_timeout(30)
        .build()
    )

    # Обработчики
    app.add_handler(CommandHandler("start", handle_start))
    app.add_handler(CommandHandler("collect", cmd_collect))
    app.add_handler(get_post_conversation_handler())
    app.add_handler(get_competitor_conversation_handler())
    app.add_handler(get_commenting_conversation_handler())
    app.add_handler(MessageHandler(filters.Text(["🎬 Рилсы"]), handle_reels_button))
    app.add_handler(MessageHandler(filters.Text(["📊 Аналитика"]), handle_analytics_button))
    app.add_handler(CallbackQueryHandler(handle_analytics_callback, pattern=r"^analytics_"))
    app.add_handler(CallbackQueryHandler(handle_hooks_button, pattern=r"^hooks_analysis$"))
    app.add_handler(CallbackQueryHandler(handle_scenario_button, pattern=r"^scenario_\d+$"))

    # Ежедневная задача в 9:00
    job_queue = app.job_queue
    job_queue.run_daily(daily_job, time=time(hour=9, minute=0, second=0))

    # Запуск бота
    app.run_polling()


if __name__ == "__main__":
    main()
