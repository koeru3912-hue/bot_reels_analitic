"""Управление конкурентами и просмотр отчётов."""

import logging
import asyncio

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

from analytics.competitors import (
    get_competitors,
    add_competitor,
    remove_competitor,
    get_competitor_report,
)

logger = logging.getLogger(__name__)

AWAITING_CHANNEL = 0


async def handle_competitors_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Кнопка 'Конкуренты' — показывает меню."""
    competitors = get_competitors()

    keyboard = [
        [
            InlineKeyboardButton("📊 Отчёт", callback_data="comp_report"),
            InlineKeyboardButton("➕ Добавить", callback_data="comp_add"),
        ],
    ]

    if competitors:
        keyboard.append(
            [InlineKeyboardButton("🗑 Удалить", callback_data="comp_remove")]
        )

    keyboard.append(
        [InlineKeyboardButton("❌ Закрыть", callback_data="comp_close")]
    )

    channels_text = "\n".join(f"  • @{ch}" for ch in competitors) if competitors else "  (пусто)"

    msg_text = (
        f"🔍 Конкуренты ({len(competitors)})\n\n"
        f"Отслеживаемые каналы:\n{channels_text}\n"
    )

    await update.message.reply_text(
        msg_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

    return AWAITING_CHANNEL


async def handle_comp_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обрабатывает действия с конкурентами."""
    query = update.callback_query
    await query.answer()

    if query.data == "comp_close":
        await query.message.edit_text("🔍 Конкуренты — закрыто.")
        return ConversationHandler.END

    if query.data == "comp_add":
        await query.message.edit_text(
            "➕ Отправьте username канала конкурента.\n\n"
            "Можно в любом формате:\n"
            "• @channelname\n"
            "• channelname\n"
            "• https://t.me/channelname"
        )
        context.user_data["comp_action"] = "add"
        return AWAITING_CHANNEL

    if query.data == "comp_remove":
        competitors = get_competitors()
        if not competitors:
            await query.message.edit_text("Список конкурентов пуст.")
            return ConversationHandler.END

        buttons = []
        for ch in competitors:
            buttons.append(
                [InlineKeyboardButton(f"🗑 @{ch}", callback_data=f"comp_del_{ch}")]
            )
        buttons.append(
            [InlineKeyboardButton("⬅️ Назад", callback_data="comp_back")]
        )

        await query.message.edit_text(
            "🗑 Выберите канал для удаления:",
            reply_markup=InlineKeyboardMarkup(buttons),
        )
        return AWAITING_CHANNEL

    if query.data == "comp_report":
        await query.message.edit_text("⏳ Загружаю данные конкурентов...")

        report = await asyncio.get_event_loop().run_in_executor(
            None, get_competitor_report
        )

        try:
            await query.message.edit_text(report, parse_mode="Markdown",
                                          disable_web_page_preview=True)
        except Exception:
            await query.message.edit_text(report, disable_web_page_preview=True)
        return ConversationHandler.END

    if query.data.startswith("comp_del_"):
        channel = query.data.replace("comp_del_", "")
        removed = remove_competitor(channel)
        if removed:
            await query.message.edit_text(f"✅ @{channel} удалён из конкурентов.")
        else:
            await query.message.edit_text(f"⚠️ @{channel} не найден.")
        return ConversationHandler.END

    if query.data == "comp_back":
        # Вернуться в главное меню конкурентов
        competitors = get_competitors()
        keyboard = [
            [
                InlineKeyboardButton("📊 Отчёт", callback_data="comp_report"),
                InlineKeyboardButton("➕ Добавить", callback_data="comp_add"),
            ],
        ]
        if competitors:
            keyboard.append(
                [InlineKeyboardButton("🗑 Удалить", callback_data="comp_remove")]
            )
        keyboard.append(
            [InlineKeyboardButton("❌ Закрыть", callback_data="comp_close")]
        )

        channels_text = "\n".join(f"  • @{ch}" for ch in competitors) if competitors else "  (пусто)"

        await query.message.edit_text(
            f"🔍 Конкуренты ({len(competitors)})\n\n"
            f"Отслеживаемые каналы:\n{channels_text}\n",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return AWAITING_CHANNEL

    return AWAITING_CHANNEL


async def handle_channel_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Пользователь ввёл username канала."""
    action = context.user_data.pop("comp_action", "")
    text = update.message.text.strip()

    if action == "add":
        channel = add_competitor(text)
        await update.message.reply_text(f"✅ @{channel} добавлен в конкуренты!")
    else:
        await update.message.reply_text("⚠️ Неизвестное действие.")

    return ConversationHandler.END


def get_competitor_conversation_handler() -> ConversationHandler:
    """Возвращает ConversationHandler для управления конкурентами."""
    return ConversationHandler(
        entry_points=[
            MessageHandler(filters.Text(["🔍 Конкуренты"]), handle_competitors_button),
        ],
        states={
            AWAITING_CHANNEL: [
                CallbackQueryHandler(
                    handle_comp_action,
                    pattern=r"^comp_(report|add|remove|close|back|del_.+)$",
                ),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_channel_input),
            ],
        },
        fallbacks=[
            MessageHandler(filters.COMMAND, lambda u, c: ConversationHandler.END),
        ],
        allow_reentry=True,
    )
