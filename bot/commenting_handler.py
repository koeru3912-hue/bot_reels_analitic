"""Нейрокомментинг — генерация комментариев для постов конкурентов."""

import logging
import asyncio

from openai import OpenAI
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

from config.settings import OPENAI_API_KEY
from analytics.competitors import fetch_all_competitors, get_competitors

logger = logging.getLogger(__name__)

# Состояния
CHOOSE_POST = 0
REVIEW_COMMENT = 1

COMMENT_PROMPT = """Ты — эксперт по AI-автоматизации для бизнеса. Напиши экспертный комментарий к посту в Telegram-канале.

Пост:
{post_text}

## Правила комментария:

ТОНАЛЬНОСТЬ:
- Экспертная, но живая — без канцелярита
- Добавляй ценность — свой опыт, наблюдение, дополнение
- Можно мягко не согласиться с частью поста, если есть аргумент
- Первое лицо — "я заметил", "у нас был кейс", "по моему опыту"

ФОРМАТ:
- 2-4 предложения, максимум 500 символов
- Без эмодзи (максимум 1, если уместно)
- Без самопиара и ссылок
- Без "отличный пост!" и "полностью согласен!"
- Комментарий должен вызывать желание ответить

ПРИМЕРЫ хороших комментариев:
- "Интересный кейс. У нас похожая ситуация была с клиникой — CRM-бот сократил время обработки заявок в 3 раза. Но главный инсайт оказался в другом — 40% клиентов вообще не звонили, а писали в мессенджер."
- "По поводу автоматизации — тут есть подводный камень. Если бот слишком 'умный', люди начинают ему доверять полностью и перестают проверять. Видел такое в двух проектах."

Напиши ТОЛЬКО текст комментария, без пояснений."""


def _generate_comment(post_text: str) -> str:
    """Генерирует комментарий через OpenAI API."""
    if not OPENAI_API_KEY:
        return "⚠️ OPENAI_API_KEY не задан."

    client = OpenAI(api_key=OPENAI_API_KEY)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": COMMENT_PROMPT.format(post_text=post_text)}],
    )
    return response.choices[0].message.content


async def handle_commenting_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Кнопка 'Комментинг' — загружаем посты конкурентов."""
    competitors = get_competitors()
    if not competitors:
        await update.message.reply_text(
            "💬 *Нейрокомментинг*\n\n"
            "Сначала добавьте конкурентов:\n"
            "нажмите 🔍 *Конкуренты* → *Добавить канал*",
            parse_mode="Markdown",
        )
        return ConversationHandler.END

    await update.message.reply_text("⏳ Загружаю посты конкурентов...")

    posts = await asyncio.get_event_loop().run_in_executor(
        None, fetch_all_competitors, 3
    )

    if not posts:
        await update.message.reply_text("⚠️ Не удалось загрузить посты конкурентов.")
        return ConversationHandler.END

    # Сохраняем посты в контексте
    context.user_data["comment_posts"] = posts

    # Показываем список постов для выбора
    lines = ["💬 *Нейрокомментинг*\n\nВыберите пост для комментария:\n"]
    buttons = []

    for i, post in enumerate(posts[:8]):
        preview = post["text"][:60].replace("\n", " ")
        channel = post.get("channel", "")
        views = post.get("views", 0)
        lines.append(f"*{i+1}.* @{channel} — {preview}...\n   👁 {views:,}")
        buttons.append(
            InlineKeyboardButton(str(i + 1), callback_data=f"comment_{i}")
        )

    # Располагаем кнопки по 4 в ряд
    rows = [buttons[i:i+4] for i in range(0, len(buttons), 4)]
    rows.append([InlineKeyboardButton("❌ Отмена", callback_data="comment_cancel")])

    await update.message.reply_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(rows),
        parse_mode="Markdown",
        disable_web_page_preview=True,
    )

    return CHOOSE_POST


async def handle_choose_post(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Пользователь выбрал пост — генерируем комментарий."""
    query = update.callback_query
    await query.answer()

    if query.data == "comment_cancel":
        context.user_data.pop("comment_posts", None)
        await query.message.edit_text("❌ Отменено.")
        return ConversationHandler.END

    idx = int(query.data.split("_")[1])
    posts = context.user_data.get("comment_posts", [])

    if idx >= len(posts):
        await query.message.edit_text("⚠️ Пост не найден.")
        return ConversationHandler.END

    post = posts[idx]
    context.user_data["comment_target_post"] = post

    await query.message.edit_text("⏳ Генерирую комментарий...")

    try:
        comment = await asyncio.get_event_loop().run_in_executor(
            None, _generate_comment, post["text"]
        )
    except Exception as e:
        logger.error(f"Ошибка генерации комментария: {e}")
        await query.message.edit_text(f"⚠️ Ошибка: {e}")
        return ConversationHandler.END

    context.user_data["generated_comment"] = comment

    post_url = post.get("url", "")
    channel = post.get("channel", "")

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📋 Скопировать", callback_data="comment_copy"),
            InlineKeyboardButton("🔄 Переписать", callback_data="comment_retry"),
        ],
        [
            InlineKeyboardButton("⬅️ К списку", callback_data="comment_back"),
            InlineKeyboardButton("❌ Отмена", callback_data="comment_done"),
        ],
    ])

    await query.message.edit_text(
        f"💬 *Комментарий к посту @{channel}:*\n\n"
        f"```\n{comment}\n```\n\n"
        f"🔗 [Перейти к посту]({post_url})\n\n"
        f"Скопируйте комментарий и вставьте под постом.",
        reply_markup=keyboard,
        parse_mode="Markdown",
        disable_web_page_preview=True,
    )

    return REVIEW_COMMENT


async def handle_review_comment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обрабатывает действия с комментарием."""
    query = update.callback_query
    await query.answer()

    if query.data == "comment_done":
        context.user_data.pop("comment_posts", None)
        context.user_data.pop("comment_target_post", None)
        context.user_data.pop("generated_comment", None)
        await query.message.edit_text("✅ Готово!")
        return ConversationHandler.END

    if query.data == "comment_copy":
        comment = context.user_data.get("generated_comment", "")
        # Отправляем чистый текст без форматирования для удобного копирования
        await query.message.reply_text(comment)
        return REVIEW_COMMENT

    if query.data == "comment_retry":
        post = context.user_data.get("comment_target_post", {})
        if not post:
            await query.message.edit_text("⚠️ Пост не найден.")
            return ConversationHandler.END

        await query.message.edit_text("⏳ Переписываю комментарий...")

        try:
            comment = await asyncio.get_event_loop().run_in_executor(
                None, _generate_comment, post["text"]
            )
        except Exception as e:
            await query.message.edit_text(f"⚠️ Ошибка: {e}")
            return ConversationHandler.END

        context.user_data["generated_comment"] = comment
        channel = post.get("channel", "")
        post_url = post.get("url", "")

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📋 Скопировать", callback_data="comment_copy"),
                InlineKeyboardButton("🔄 Переписать", callback_data="comment_retry"),
            ],
            [
                InlineKeyboardButton("⬅️ К списку", callback_data="comment_back"),
                InlineKeyboardButton("❌ Отмена", callback_data="comment_done"),
            ],
        ])

        await query.message.edit_text(
            f"💬 *Комментарий к посту @{channel}:*\n\n"
            f"```\n{comment}\n```\n\n"
            f"🔗 [Перейти к посту]({post_url})\n\n"
            f"Скопируйте комментарий и вставьте под постом.",
            reply_markup=keyboard,
            parse_mode="Markdown",
            disable_web_page_preview=True,
        )

        return REVIEW_COMMENT

    if query.data == "comment_back":
        # Возвращаемся к списку постов
        posts = context.user_data.get("comment_posts", [])
        if not posts:
            await query.message.edit_text("⚠️ Нет данных. Нажмите 💬 Комментинг заново.")
            return ConversationHandler.END

        lines = ["💬 *Нейрокомментинг*\n\nВыберите пост для комментария:\n"]
        buttons = []

        for i, post in enumerate(posts[:8]):
            preview = post["text"][:60].replace("\n", " ")
            channel = post.get("channel", "")
            views = post.get("views", 0)
            lines.append(f"*{i+1}.* @{channel} — {preview}...\n   👁 {views:,}")
            buttons.append(
                InlineKeyboardButton(str(i + 1), callback_data=f"comment_{i}")
            )

        rows = [buttons[i:i+4] for i in range(0, len(buttons), 4)]
        rows.append([InlineKeyboardButton("❌ Отмена", callback_data="comment_cancel")])

        await query.message.edit_text(
            "\n".join(lines),
            reply_markup=InlineKeyboardMarkup(rows),
            parse_mode="Markdown",
            disable_web_page_preview=True,
        )

        return CHOOSE_POST

    return REVIEW_COMMENT


def get_commenting_conversation_handler() -> ConversationHandler:
    """Возвращает ConversationHandler для нейрокомментинга."""
    return ConversationHandler(
        entry_points=[
            MessageHandler(filters.Text(["💬 Комментинг"]), handle_commenting_button),
        ],
        states={
            CHOOSE_POST: [
                CallbackQueryHandler(
                    handle_choose_post, pattern=r"^comment_(\d+|cancel)$"
                ),
            ],
            REVIEW_COMMENT: [
                CallbackQueryHandler(
                    handle_review_comment,
                    pattern=r"^comment_(copy|retry|back|done)$",
                ),
            ],
        },
        fallbacks=[
            MessageHandler(filters.COMMAND, lambda u, c: ConversationHandler.END),
        ],
        allow_reentry=True,
    )
