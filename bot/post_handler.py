import logging
import asyncio
from pathlib import Path

from openai import OpenAI
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

from config.settings import TEMP_VIDEO_DIR, OPENAI_API_KEY, TELEGRAM_CHANNEL_ID, MAX_BOT_TOKEN
from publisher.max_channel import publish_to_max
from analytics.channel_stats import log_published_post

logger = logging.getLogger(__name__)

# Состояния
AWAITING_VOICE = 0
REVIEW_POST = 1
AWAITING_MEDIA = 2
AWAITING_EDIT = 3

POST_PROMPT = """Ты — редактор, который оформляет мысли автора в пост для Telegram-канала.

Транскрипция голосового сообщения автора:
{transcription}

## Главное правило:

СОХРАНЯЙ МЫСЛЬ АВТОРА. Голосовое — это черновик поста. Автор уже продумал что сказать, в каком порядке и с какими акцентами. Твоя задача — отредактировать, а НЕ переписать.

Что делать:
- Сохрани структуру и порядок мыслей из голосового
- Сохрани все ключевые идеи, примеры и аргументы автора
- Убери слова-паразиты, повторы, устную "воду"
- Сделай текст читаемым: разбей на абзацы, добавь заголовок
- Если автор привёл пример или историю — обязательно оставь

Чего НЕ делать:
- Не добавляй свои идеи, примеры и аргументы
- Не меняй позицию и выводы автора
- Не придумывай то, чего не было в голосовом
- Не переставляй мысли в другом порядке

## Стиль оформления:

ТОНАЛЬНОСТЬ:
- Живой разговорный язык — как будто рассказываешь другу за кофе
- Прямолинейность — не сглаживай углы
- Первое лицо — "я понял", "я сделал", "меня бесит"

ФОРМАТ:
- Цепляющий заголовок (короткий, из сути поста)
- Короткие абзацы, 1-3 предложения
- Рубленые предложения. Иногда из одного слова. Так.
- Длинное тире «—» для пауз
- Эмодзи: максимум 2-3, только если уместно
- Длина: 800-2000 символов
- Без хештегов
- Не начинай с "Друзья!" или "Всем привет!"

Напиши только текст поста, без пояснений."""


def _post_keyboard(has_media: bool = False) -> InlineKeyboardMarkup:
    """Клавиатура для поста."""
    media_label = "🔄 Заменить медиа" if has_media else "📎 Добавить медиа"
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📢 Опубликовать", callback_data="post_publish"),
            InlineKeyboardButton("✏️ Редактировать", callback_data="post_edit"),
        ],
        [
            InlineKeyboardButton("🔄 Переписать", callback_data="post_retry"),
            InlineKeyboardButton(media_label, callback_data="post_add_media"),
        ],
        [
            InlineKeyboardButton("❌ Отмена", callback_data="post_cancel"),
        ],
    ])


def _transcribe_voice(file_path: str) -> str:
    """Транскрибирует голосовое сообщение через OpenAI Whisper API."""
    client = OpenAI(api_key=OPENAI_API_KEY, timeout=120)
    with open(file_path, "rb") as f:
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=f,
            language="ru",
        )
    return transcript.text


def _generate_post(transcription: str) -> str:
    """Генерирует пост через OpenAI API."""
    if not OPENAI_API_KEY:
        return f"⚠️ OPENAI_API_KEY не задан.\n\nВаш текст:\n{transcription}"

    client = OpenAI(api_key=OPENAI_API_KEY, timeout=120)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": POST_PROMPT.format(transcription=transcription)}],
    )
    return response.choices[0].message.content


async def handle_post_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Кнопка 'Написать пост' — просим голосовое."""
    await update.message.reply_text(
        "🎙 *Написать пост*\n\n"
        "Запишите голосовое сообщение — расскажите, о чём хотите написать пост.\n\n"
        "Я транскрибирую его и сгенерирую готовый пост для Telegram-канала.",
        parse_mode="Markdown",
    )
    return AWAITING_VOICE


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получили голосовое — транскрибируем и генерируем пост."""
    voice = update.message.voice or update.message.audio
    if not voice:
        await update.message.reply_text("Отправьте голосовое сообщение (кнопка 🎙).")
        return AWAITING_VOICE

    await update.message.reply_text("⏳ Транскрибирую голосовое...")

    # Скачиваем файл
    TEMP_VIDEO_DIR.mkdir(parents=True, exist_ok=True)
    file_path = str(TEMP_VIDEO_DIR / f"voice_{update.effective_user.id}.ogg")

    tg_file = await voice.get_file()
    await tg_file.download_to_drive(file_path)

    # Транскрипция
    try:
        transcription = await asyncio.get_event_loop().run_in_executor(
            None, _transcribe_voice, file_path
        )
    except Exception as e:
        logger.error(f"Ошибка транскрипции: {e}")
        await update.message.reply_text(f"⚠️ Ошибка транскрипции: {e}")
        _cleanup_voice(file_path)
        return ConversationHandler.END

    if not transcription:
        await update.message.reply_text("⚠️ Не удалось распознать речь. Попробуйте ещё раз.")
        _cleanup_voice(file_path)
        return AWAITING_VOICE

    await update.message.reply_text(
        f"✅ Распознано:\n_{transcription}_\n\n⏳ Генерирую пост...",
        parse_mode="Markdown",
    )

    context.user_data["voice_transcription"] = transcription

    # Генерация поста
    try:
        post_text = await asyncio.get_event_loop().run_in_executor(
            None, _generate_post, transcription
        )
    except Exception as e:
        logger.error(f"Ошибка генерации поста: {e}")
        await update.message.reply_text(f"⚠️ Ошибка генерации: {e}")
        _cleanup_voice(file_path)
        return ConversationHandler.END

    context.user_data["generated_post"] = post_text
    _cleanup_voice(file_path)

    await update.message.reply_text(
        f"📝 *Готовый пост:*\n\n{post_text}",
        reply_markup=_post_keyboard(),
        parse_mode="Markdown",
    )

    return REVIEW_POST


async def handle_post_review(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обрабатывает решение по посту."""
    query = update.callback_query
    await query.answer()

    if query.data == "post_cancel":
        context.user_data.pop("voice_transcription", None)
        context.user_data.pop("generated_post", None)
        await query.message.edit_text("❌ Отменено.")
        return ConversationHandler.END

    if query.data == "post_retry":
        transcription = context.user_data.get("voice_transcription", "")
        if not transcription:
            await query.message.edit_text("⚠️ Нет транскрипции. Отправьте голосовое ещё раз.")
            return ConversationHandler.END

        await query.message.edit_text("⏳ Переписываю пост...")

        try:
            post_text = await asyncio.get_event_loop().run_in_executor(
                None, _generate_post, transcription
            )
        except Exception as e:
            await query.message.edit_text(f"⚠️ Ошибка: {e}")
            return ConversationHandler.END

        context.user_data["generated_post"] = post_text
        context.user_data.pop("post_media", None)

        await query.message.edit_text(
            f"📝 *Готовый пост:*\n\n{post_text}",
            reply_markup=_post_keyboard(),
            parse_mode="Markdown",
        )

        return REVIEW_POST

    if query.data == "post_edit":
        post_text = context.user_data.get("generated_post", "")
        await query.message.edit_text(
            "✏️ Отправьте исправленный текст поста.\n\n"
            "Текущий текст скопирован ниже — отредактируйте и отправьте:"
        )
        # Отправляем текст отдельным сообщением для удобного копирования
        await query.message.reply_text(post_text)
        return AWAITING_EDIT

    if query.data == "post_add_media":
        await query.message.edit_text(
            "📎 Отправьте фото, видео или файл для поста.",
        )
        return AWAITING_MEDIA

    if query.data == "post_publish":
        post_text = context.user_data.get("generated_post", "")
        media = context.user_data.pop("post_media", None)
        context.user_data.pop("voice_transcription", None)
        context.user_data.pop("generated_post", None)

        results = []

        # 1. Публикация в Telegram
        if TELEGRAM_CHANNEL_ID:
            try:
                if media:
                    media_type = media["type"]
                    file_id = media["file_id"]
                    if media_type == "photo":
                        await context.bot.send_photo(
                            chat_id=TELEGRAM_CHANNEL_ID,
                            photo=file_id,
                            caption=post_text,
                        )
                    elif media_type == "video":
                        await context.bot.send_video(
                            chat_id=TELEGRAM_CHANNEL_ID,
                            video=file_id,
                            caption=post_text,
                        )
                    elif media_type == "document":
                        await context.bot.send_document(
                            chat_id=TELEGRAM_CHANNEL_ID,
                            document=file_id,
                            caption=post_text,
                        )
                else:
                    await context.bot.send_message(
                        chat_id=TELEGRAM_CHANNEL_ID,
                        text=post_text,
                    )
                results.append("✅ Telegram")
            except Exception as e:
                logger.error(f"Ошибка публикации в Telegram: {e}")
                results.append(f"❌ Telegram: {e}")
        else:
            results.append("⚠️ Telegram: TELEGRAM_CHANNEL_ID не задан")

        # 2. Публикация в Max
        if MAX_BOT_TOKEN:
            try:
                # Скачиваем фото для Max если есть
                max_photo_path = None
                if media and media["type"] == "photo":
                    TEMP_VIDEO_DIR.mkdir(parents=True, exist_ok=True)
                    max_photo_path = str(TEMP_VIDEO_DIR / "max_post_photo.jpg")
                    tg_file = await context.bot.get_file(media["file_id"])
                    await tg_file.download_to_drive(max_photo_path)

                max_result = await asyncio.get_event_loop().run_in_executor(
                    None, publish_to_max, post_text, max_photo_path
                )
                results.append("✅ Max")

                # Удаляем временное фото
                if max_photo_path:
                    Path(max_photo_path).unlink(missing_ok=True)
            except Exception as e:
                logger.error(f"Ошибка публикации в Max: {e}")
                results.append(f"❌ Max: {e}")
        else:
            results.append("⚠️ Max: MAX_BOT_TOKEN не задан")

        # Логируем публикацию для аналитики
        published_platforms = [r.split()[1] for r in results if r.startswith("✅")]
        if published_platforms:
            log_published_post(
                text=post_text,
                platforms=published_platforms,
                has_media=media is not None,
                media_type=media["type"] if media else "",
            )

        status = "\n".join(results)
        await query.message.edit_text(f"📢 Результаты публикации:\n\n{status}")
        return ConversationHandler.END

    return REVIEW_POST


async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получили медиа — сохраняем file_id и возвращаем к обзору поста."""
    msg = update.message

    if msg.photo:
        context.user_data["post_media"] = {"type": "photo", "file_id": msg.photo[-1].file_id}
        media_label = "фото"
    elif msg.video:
        context.user_data["post_media"] = {"type": "video", "file_id": msg.video.file_id}
        media_label = "видео"
    elif msg.document:
        context.user_data["post_media"] = {"type": "document", "file_id": msg.document.file_id}
        media_label = "файл"
    else:
        await msg.reply_text("Отправьте фото, видео или файл.")
        return AWAITING_MEDIA

    post_text = context.user_data.get("generated_post", "")

    await msg.reply_text(
        f"📝 *Готовый пост:*\n\n{post_text}\n\n📎 Прикреплено: {media_label}",
        reply_markup=_post_keyboard(has_media=True),
        parse_mode="Markdown",
    )
    return REVIEW_POST


async def handle_edit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Пользователь отправил отредактированный текст поста."""
    new_text = update.message.text.strip()
    if not new_text:
        await update.message.reply_text("Отправьте текст поста.")
        return AWAITING_EDIT

    context.user_data["generated_post"] = new_text
    has_media = "post_media" in context.user_data

    await update.message.reply_text(
        f"📝 *Обновлённый пост:*\n\n{new_text}",
        reply_markup=_post_keyboard(has_media=has_media),
        parse_mode="Markdown",
    )
    return REVIEW_POST


def _cleanup_voice(file_path: str):
    """Удаляет временный файл голосового."""
    try:
        Path(file_path).unlink(missing_ok=True)
    except Exception:
        pass


def get_post_conversation_handler() -> ConversationHandler:
    """Возвращает ConversationHandler для генерации постов из голосовых."""
    return ConversationHandler(
        entry_points=[
            MessageHandler(filters.Text(["✍️ Написать пост"]), handle_post_button),
        ],
        states={
            AWAITING_VOICE: [
                MessageHandler(filters.VOICE | filters.AUDIO, handle_voice),
            ],
            REVIEW_POST: [
                CallbackQueryHandler(
                    handle_post_review, pattern=r"^post_(publish|retry|cancel|add_media|edit)$"
                ),
            ],
            AWAITING_MEDIA: [
                MessageHandler(
                    filters.PHOTO | filters.VIDEO | filters.Document.ALL,
                    handle_media,
                ),
            ],
            AWAITING_EDIT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_edit),
            ],
        },
        fallbacks=[
            MessageHandler(filters.COMMAND, lambda u, c: ConversationHandler.END),
        ],
        allow_reentry=True,
    )
