import os
import logging
import asyncio
from pathlib import Path

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

from config.settings import OPENAI_API_KEY, TEMP_VIDEO_DIR

logger = logging.getLogger(__name__)

# Состояния
AWAITING_VOICE = 0
REVIEW_POST = 1

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

POST_PROMPT = """Ты — копирайтер, который пишет посты для Telegram-канала в авторском стиле.

Транскрипция голосового сообщения (тема поста):
{transcription}

## Авторский стиль — строго следуй ему:

ТОНАЛЬНОСТЬ:
- Живой разговорный язык — как будто рассказываешь другу за кофе
- Прямолинейность и честность — не сглаживай углы, говори как есть
- Лёгкая провокация — не бойся резких выводов и сильных утверждений
- Первое лицо — "я понял", "я сделал", "меня бесит"

СТРУКТУРА:
- Цепляющий заголовок (короткий, без эмодзи)
- Личная история или наблюдение как вход в тему
- Нумерованные пункты (1., 2., 3.) для ключевых мыслей
- Короткие рубленые предложения. Иногда — из одного слова. Так.
- Длинное тире «—» вместо запятых и для пауз
- Вопрос к аудитории или CTA в конце поста

ФОРМАТ:
- Эмодзи: максимум 2-3 на весь пост, только если уместно (🥊, 🤘, 🎯). Не ставь эмодзи в каждый абзац
- Нумерация: цифры с точкой или эмодзи-цифры (1⃣, 2⃣, 3⃣)
- Длина: 800-2000 символов
- Абзацы: короткие, 1-3 предложения, между ними пустая строка
- Без хештегов в конце

ЧЕГО НЕ ДЕЛАТЬ:
- Не начинай с "Друзья!" или "Всем привет!"
- Не пиши канцеляритом и маркетинговыми клише
- Не ставь эмодзи через слово
- Не добавляй "подписывайтесь" или "ставьте лайк"
- Не пиши "в данной статье", "хочу поделиться"

ПРИМЕРЫ фраз в стиле автора:
- "Благополучно забил на визит к врачу. Мужицкая логика: копьё из груди не торчит — значит, ничего страшного."
- "И возникает ощущение, что клинике на меня насрать )"
- "Прежде чем стать достойным, нужно выжить. Только сильный — может оберегать слабых."
- "Сколько людей разворачиваются в этот момент?"

Напиши только текст поста, без пояснений и комментариев."""


def _transcribe_voice(file_path: str) -> str:
    """Транскрибирует голосовое сообщение через OpenAI Whisper API."""
    import requests

    if not OPENAI_API_KEY:
        return ""

    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}

    with open(file_path, "rb") as f:
        resp = requests.post(
            "https://api.openai.com/v1/audio/transcriptions",
            headers=headers,
            files={"file": (Path(file_path).name, f, "audio/ogg")},
            data={"model": "whisper-1", "language": "ru"},
            timeout=60,
        )

    resp.raise_for_status()
    return resp.json().get("text", "")


def _generate_post(transcription: str) -> str:
    """Генерирует пост через OpenRouter."""
    import requests

    if not OPENROUTER_API_KEY:
        return f"⚠️ OPENROUTER_API_KEY не задан.\n\nВаш текст:\n{transcription}"

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "google/gemma-3-4b-it:free",
        "messages": [{"role": "user", "content": POST_PROMPT.format(transcription=transcription)}],
    }

    resp = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=120)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


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

    if not OPENAI_API_KEY:
        await update.message.reply_text("⚠️ OPENAI_API_KEY не задан. Транскрипция недоступна.")
        return ConversationHandler.END

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

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Готово", callback_data="post_accept"),
            InlineKeyboardButton("🔄 Переписать", callback_data="post_retry"),
        ],
        [InlineKeyboardButton("❌ Отмена", callback_data="post_cancel")],
    ])

    await update.message.reply_text(
        f"📝 *Готовый пост:*\n\n{post_text}",
        reply_markup=keyboard,
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

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Готово", callback_data="post_accept"),
                InlineKeyboardButton("🔄 Переписать", callback_data="post_retry"),
            ],
            [InlineKeyboardButton("❌ Отмена", callback_data="post_cancel")],
        ])

        await query.message.edit_text(
            f"📝 *Готовый пост:*\n\n{post_text}",
            reply_markup=keyboard,
            parse_mode="Markdown",
        )

        return REVIEW_POST

    if query.data == "post_accept":
        post_text = context.user_data.get("generated_post", "")
        context.user_data.pop("voice_transcription", None)
        context.user_data.pop("generated_post", None)

        await query.message.edit_text(
            f"✅ *Пост готов! Скопируйте и опубликуйте:*\n\n{post_text}",
            parse_mode="Markdown",
        )
        return ConversationHandler.END

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
                    handle_post_review, pattern=r"^post_(accept|retry|cancel)$"
                ),
            ],
        },
        fallbacks=[
            MessageHandler(filters.COMMAND, lambda u, c: ConversationHandler.END),
        ],
        allow_reentry=True,
    )
