# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
source .venv/bin/activate && python main.py        # запуск бота
source .venv/bin/activate && python test_send.py    # интеграционный тест (YouTube + Telegram)
pip install -r requirements.txt                     # установка зависимостей
python scripts/youtube_auth.py --client-id=ID --client-secret=SECRET  # получение YouTube OAuth2 refresh token
```

Системная зависимость: `ffmpeg` (извлечение обложек из видео).

## Architecture

Telegram-бот для аналитики короткого видео и публикации контента. Python 3.9, async (python-telegram-bot v22+).

### Data pipeline (аналитика)

```
parsers/{youtube,vk}.py → analytics/scorer.py → bot/telegram_bot.py → Telegram
                           (relevance filter     (save JSON + send       (inline buttons)
                            + weighted scoring)    top-5 message)
                                                       ↓
                                              generator/gemini.py
                                              (AI сценарий через OpenRouter)
```

### Publishing pipeline (публикация)

```
Telegram video upload → bot/publish_handler.py (ConversationHandler)
    → publisher/whisper_srt.py (Whisper API → SRT)
    → publisher/cover.py (ffmpeg → cover.jpg)
    → publisher/storage.py (public URL for Instagram)
    → publisher/{youtube_shorts,vk_clips,instagram}.py
```

`publish_handler.py` использует `ConversationHandler` с состояниями: `VIDEO_RECEIVED → AWAITING_DETAILS → AWAITING_COVER → CONFIRM_PUBLISH`. Каждая площадка публикуется независимо — ошибка одной не блокирует другие.

### Key patterns

- Все API-ключи загружаются через `config/settings.py` из `.env` (python-dotenv)
- AI-генерация (сценарии, хештеги) идёт через OpenRouter API (`google/gemma-3-4b-it:free`) — паттерн в `generator/gemini.py`
- Синхронные API-вызовы в publisher/ оборачиваются в `run_in_executor` для совместимости с async-ботом
- Данные топ-5 кэшируются в `data/top_content.json` между нажатиями кнопок
- Scoring: `views×1 + likes×2 + comments×3 + reposts×4`, фильтрация по ключевым словам из `config/keywords.py`

### Auth differences

- `YOUTUBE_API_KEY` — только чтение (поиск). Для загрузки видео нужен OAuth2 (`YOUTUBE_CLIENT_ID` + `SECRET` + `REFRESH_TOKEN`)
- `VK_TOKEN` — service token для поиска. Для публикации нужен `VK_USER_TOKEN` с scope `video,wall`
- Instagram Graph API требует публичный URL видео (через `publisher/storage.py`) и 60-дневный токен
