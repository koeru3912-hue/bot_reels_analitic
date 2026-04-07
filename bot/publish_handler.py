import os
import logging
import asyncio
from pathlib import Path
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

from config.settings import OPENAI_API_KEY, TEMP_VIDEO_DIR
from publisher.whisper_srt import generate_srt
from publisher.cover import extract_cover
# from publisher.storage import upload_to_public_url       # TODO: включить для Instagram
# from publisher.instagram import publish_to_instagram     # TODO: включить позже
# from publisher.vk_clips import publish_to_vk             # TODO: включить позже
from publisher.youtube_shorts import publish_to_youtube

logger = logging.getLogger(__name__)

# Состояния ConversationHandler
AWAITING_DETAILS, AWAITING_COVER, CONFIRM_PUBLISH = range(3)

# OpenRouter для генерации описания/хештегов (переиспользуем паттерн из gemini.py)
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

HASHTAG_PROMPT = """Ты — SMM-эксперт. Напиши короткое описание (2-3 предложения) и 10-15 хештегов для короткого вертикального видео (Reels/Shorts/TikTok).

Тематика: AI-автоматизация, нейросети для бизнеса, чат-боты, автоматизация записи клиентов.

Формат ответа (строго):
ОПИСАНИЕ:
[текст описания]

ХЕШТЕГИ:
#тег1 #тег2 #тег3 ...

Пиши на русском. Хештеги — смесь русских и английских."""


def _generate_details_ai() -> tuple[str, str]:
    """Генерирует описание и хештеги через OpenRouter."""
    import requests

    if not OPENROUTER_API_KEY:
        return ("", "")

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "google/gemma-3-4b-it:free",
        "messages": [{"role": "user", "content": HASHTAG_PROMPT}],
    }

    try:
        resp = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=60)
        resp.raise_for_status()
        text = resp.json()["choices"][0]["message"]["content"]

        # Парсим ответ
        description = ""
        hashtags = ""

        if "ОПИСАНИЕ:" in text and "ХЕШТЕГИ:" in text:
            parts = text.split("ХЕШТЕГИ:")
            description = parts[0].replace("ОПИСАНИЕ:", "").strip()
            hashtags = parts[1].strip()
        else:
            # Пробуем извлечь хештеги из текста
            lines = text.strip().split("\n")
            hashtag_lines = [l for l in lines if "#" in l]
            other_lines = [l for l in lines if "#" not in l and l.strip()]
            description = " ".join(other_lines[:3])
            hashtags = " ".join(hashtag_lines)

        return (description, hashtags)

    except Exception as e:
        logger.error(f"Ошибка генерации описания: {e}")
        return ("", "")


async def handle_video_upload(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Пользователь отправил видео — сохраняем и спрашиваем детали."""
    message = update.message

    # Получаем файл (видео или документ)
    if message.video:
        file_obj = message.video
        file_size = message.video.file_size
    elif message.document and message.document.mime_type and message.document.mime_type.startswith("video/"):
        file_obj = message.document
        file_size = message.document.file_size
    else:
        return ConversationHandler.END

    # Проверка размера (20 МБ лимит Telegram Bot API)
    if file_size and file_size > 20 * 1024 * 1024:
        await message.reply_text(
            "⚠️ Файл слишком большой (макс. 20 МБ).\n"
            "Сожмите видео и отправьте снова."
        )
        return ConversationHandler.END

    await message.reply_text("⏳ Загружаю видео...")

    TEMP_VIDEO_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f"{update.effective_user.id}_{timestamp}.mp4"
    file_path = str(TEMP_VIDEO_DIR / file_name)

    tg_file = await file_obj.get_file()
    await tg_file.download_to_drive(file_path)

    context.user_data["pending_video"] = file_path
    logger.info(f"Видео сохранено: {file_path}")

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🤖 Сгенерировать", callback_data="pub_generate"),
            InlineKeyboardButton("✍️ Ввести вручную", callback_data="pub_manual"),
        ]
    ])

    await message.reply_text(
        "✅ Видео загружено!\n\n"
        "Как задать описание и хештеги?",
        reply_markup=keyboard,
    )

    return AWAITING_DETAILS


async def handle_details_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обрабатывает выбор: сгенерировать или ввести вручную."""
    query = update.callback_query
    await query.answer()

    if query.data == "pub_generate":
        await query.message.edit_text("⏳ Генерирую описание и хештеги...")

        description, hashtags = await asyncio.get_event_loop().run_in_executor(
            None, _generate_details_ai
        )

        if not description and not hashtags:
            await query.message.edit_text(
                "⚠️ Не удалось сгенерировать. Введите описание и хештеги вручную.\n\n"
                "Формат:\n"
                "Первая строка — описание\n"
                "Вторая строка — хештеги через пробел"
            )
            return AWAITING_DETAILS

        context.user_data["post_description"] = description
        context.user_data["post_hashtags"] = hashtags

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📸 Извлечь из видео", callback_data="cover_auto"),
                InlineKeyboardButton("🖼 Отправить фото", callback_data="cover_manual"),
            ]
        ])

        await query.message.edit_text(
            f"✅ Готово!\n\n"
            f"📝 *Описание:*\n{description}\n\n"
            f"🏷 *Хештеги:*\n{hashtags}\n\n"
            f"Теперь выберите обложку:",
            reply_markup=keyboard,
            parse_mode="Markdown",
        )

        return AWAITING_COVER

    elif query.data == "pub_manual":
        await query.message.edit_text(
            "✍️ Введите описание и хештеги.\n\n"
            "Формат:\n"
            "Первая строка — описание\n"
            "Вторая строка — хештеги через пробел\n\n"
            "Пример:\n"
            "AI-бот записывает клиентов 24/7\n"
            "#нейросети #бизнес #автоматизация #AI"
        )
        return AWAITING_DETAILS

    return AWAITING_DETAILS


async def handle_manual_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Пользователь ввёл описание и хештеги вручную."""
    text = update.message.text.strip()
    lines = text.split("\n", 1)

    description = lines[0].strip()
    hashtags = lines[1].strip() if len(lines) > 1 else ""

    context.user_data["post_description"] = description
    context.user_data["post_hashtags"] = hashtags

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📸 Извлечь из видео", callback_data="cover_auto"),
            InlineKeyboardButton("🖼 Отправить фото", callback_data="cover_manual"),
        ]
    ])

    await update.message.reply_text(
        f"✅ Сохранено!\n\n"
        f"📝 *Описание:* {description}\n"
        f"🏷 *Хештеги:* {hashtags}\n\n"
        f"Теперь выберите обложку:",
        reply_markup=keyboard,
        parse_mode="Markdown",
    )

    return AWAITING_COVER


async def handle_cover_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обрабатывает выбор обложки."""
    query = update.callback_query
    await query.answer()

    if query.data == "cover_auto":
        await query.message.edit_text("⏳ Извлекаю обложку из видео...")

        video_path = context.user_data["pending_video"]
        cover_path = await extract_cover(video_path)

        if cover_path:
            context.user_data["cover_path"] = cover_path
            await query.message.edit_text("✅ Обложка извлечена!")
        else:
            await query.message.edit_text(
                "⚠️ Не удалось извлечь обложку (нужен ffmpeg).\n"
                "Публикация продолжится без обложки."
            )

        return await _show_confirm(query.message, context)

    elif query.data == "cover_manual":
        await query.message.edit_text("🖼 Отправьте фото для обложки:")
        return AWAITING_COVER

    return AWAITING_COVER


async def handle_cover_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Пользователь отправил фото для обложки."""
    if not update.message.photo:
        await update.message.reply_text("Отправьте фото (не файл).")
        return AWAITING_COVER

    photo = update.message.photo[-1]  # максимальное разрешение
    tg_file = await photo.get_file()

    video_path = Path(context.user_data["pending_video"])
    cover_path = str(video_path.with_name(video_path.stem + "_cover.jpg"))

    await tg_file.download_to_drive(cover_path)
    context.user_data["cover_path"] = cover_path

    await update.message.reply_text("✅ Обложка сохранена!")
    return await _show_confirm(update.message, context)


async def _show_confirm(message, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Показывает превью и кнопку подтверждения."""
    description = context.user_data.get("post_description", "")
    hashtags = context.user_data.get("post_hashtags", "")
    has_cover = "cover_path" in context.user_data

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📤 Разместить пост", callback_data="pub_confirm")],
        [InlineKeyboardButton("❌ Отмена", callback_data="pub_cancel")],
    ])

    await message.reply_text(
        "📋 *Превью публикации:*\n\n"
        f"📝 {description}\n\n"
        f"🏷 {hashtags}\n\n"
        f"📸 Обложка: {'✅' if has_cover else '❌ нет'}\n"
        f"📺 Площадка: YouTube\n\n"
        f"Нажмите кнопку для публикации:",
        reply_markup=keyboard,
        parse_mode="Markdown",
    )

    return CONFIRM_PUBLISH


async def handle_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Запускает пайплайн публикации."""
    query = update.callback_query
    await query.answer()

    if query.data == "pub_cancel":
        _cleanup(context)
        await query.message.edit_text("❌ Публикация отменена.")
        return ConversationHandler.END

    if query.data != "pub_confirm":
        return CONFIRM_PUBLISH

    video_path = context.user_data["pending_video"]
    description = context.user_data.get("post_description", "")
    hashtags = context.user_data.get("post_hashtags", "")
    cover_path = context.user_data.get("cover_path")
    caption = f"{description}\n\n{hashtags}" if hashtags else description

    status_msg = await query.message.edit_text(
        "🚀 *Публикация запущена...*\n\n"
        "⏳ Генерация субтитров...",
        parse_mode="Markdown",
    )

    results = {}

    # 1. Генерация SRT субтитров
    srt_path = None
    if OPENAI_API_KEY:
        srt_content = await generate_srt(video_path)
        if srt_content:
            srt_path = str(Path(video_path).with_suffix(".srt"))
            results["Субтитры"] = "✅"
        else:
            results["Субтитры"] = "⚠️ пропущены"
    else:
        results["Субтитры"] = "⚠️ OPENAI_API_KEY не задан"

    # 2. Пу��ликация на YouTube
    await status_msg.edit_text(_format_status(results, "YouTube Shorts..."))
    try:
        yt_result = await asyncio.get_event_loop().run_in_executor(
            None, publish_to_youtube, video_path, description[:100], description, hashtags, srt_path
        )
        results["YouTube"] = f"✅ {yt_result['url']}"
    except Exception as e:
        results["YouTube"] = f"❌ {e}"
        logger.error(f"YouTube error: {e}")

    # 4. Итоговый статус
    await status_msg.edit_text(
        "🏁 *Публикация завершена!*\n\n" + _format_results(results),
        parse_mode="Markdown",
    )

    _cleanup(context)
    return ConversationHandler.END


def _format_status(results: dict, current: str) -> str:
    """Форматирует текущий статус публикации."""
    lines = ["🚀 *Публикация...*\n"]
    for key, val in results.items():
        lines.append(f"{key}: {val}")
    lines.append(f"\n⏳ {current}")
    return "\n".join(lines)


def _format_results(results: dict) -> str:
    """Форматирует итоговые результаты."""
    lines = []
    for key, val in results.items():
        lines.append(f"*{key}:* {val}")
    return "\n".join(lines)


def _cleanup(context: ContextTypes.DEFAULT_TYPE):
    """Удаляет временные файлы."""
    for key in ["pending_video", "cover_path"]:
        path = context.user_data.pop(key, None)
        if path and Path(path).exists():
            try:
                Path(path).unlink()
            except Exception:
                pass

    # Удаляем SRT если есть
    video_path = context.user_data.get("pending_video", "")
    if video_path:
        srt = Path(video_path).with_suffix(".srt")
        if srt.exists():
            try:
                srt.unlink()
            except Exception:
                pass

    context.user_data.pop("post_description", None)
    context.user_data.pop("post_hashtags", None)


def get_publish_conversation_handler() -> ConversationHandler:
    """Возвращает ConversationHandler для флоу публикации."""
    return ConversationHandler(
        entry_points=[
            MessageHandler(filters.VIDEO, handle_video_upload),
            MessageHandler(
                filters.Document.MimeType("video/mp4")
                | filters.Document.MimeType("video/quicktime"),
                handle_video_upload,
            ),
        ],
        states={
            AWAITING_DETAILS: [
                CallbackQueryHandler(handle_details_choice, pattern=r"^pub_(generate|manual)$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_manual_details),
            ],
            AWAITING_COVER: [
                CallbackQueryHandler(handle_cover_choice, pattern=r"^cover_(auto|manual)$"),
                MessageHandler(filters.PHOTO, handle_cover_photo),
            ],
            CONFIRM_PUBLISH: [
                CallbackQueryHandler(handle_confirm, pattern=r"^pub_(confirm|cancel)$"),
            ],
        },
        fallbacks=[
            MessageHandler(filters.COMMAND, lambda u, c: ConversationHandler.END),
        ],
        allow_reentry=True,
    )
