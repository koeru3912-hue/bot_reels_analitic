import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID", "")

# Количество результатов
TOP_COUNT = 5

# Время отправки (для справки, реальное расписание через launchd)
SEND_TIME = "09:00"

# OpenAI (транскрипция Whisper + генерация текстов GPT)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Max (Messenger)
MAX_BOT_TOKEN = os.getenv("MAX_BOT_TOKEN", "")
MAX_CHAT_ID = os.getenv("MAX_CHAT_ID", "")

# Временное хранилище видео
PROJECT_DIR = Path(__file__).resolve().parent.parent
TEMP_VIDEO_DIR = PROJECT_DIR / "data" / "videos"
