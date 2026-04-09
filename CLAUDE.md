# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
source .venv/bin/activate && python main.py        # запуск бота
pip install -r requirements.txt                     # установка зависимостей
```

## Architecture

Telegram-бот для аналитики короткого видео и генерации контента. Python 3.9, async (python-telegram-bot v22+).

### Data pipeline (аналитика)

```
parsers/{youtube,vk}.py → analytics/scorer.py → bot/telegram_bot.py → Telegram
                           (relevance filter     (save JSON + send       (inline buttons)
                            + weighted scoring)    top-5 message)
                                                       ↓
                                              generator/gemini.py
                                              (AI сценарий через OpenRouter)
```

### Bot handlers

| Кнопка | Handler | Назначение |
|--------|---------|-----------|
| 🎬 Рилсы | `bot/handlers.py` | Сбор топ-5 + AI-сценарии |
| ✍️ Написать пост | `bot/post_handler.py` | Генерация постов из голосовых |
| 📊 Аналитика | `bot/handlers.py` | Еженедельный отчёт, история топов |
| 🔍 Конкуренты | `bot/competitor_handler.py` | Мониторинг каналов конкурентов |
| 💬 Комментинг | `bot/commenting_handler.py` | AI-комментарии к постам |

Все диалоги используют `ConversationHandler` из python-telegram-bot.

### Key patterns

- Все API-ключи загружаются через `config/settings.py` из `.env` (python-dotenv)
- AI-генерация (сценарии, хештеги) идёт через OpenRouter API (`google/gemma-3-4b-it:free`) — паттерн в `generator/gemini.py`
- Данные топ-5 кэшируются в `data/top_content.json` между нажатиями кнопок
- Scoring: `views×1 + likes×2 + comments×3 + reposts×4`, фильтрация по ключевым словам из `config/keywords.py`
- Публикация постов в Telegram-канал + Max через `bot/post_handler.py` и `publisher/max_channel.py`
