import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# Количество результатов
TOP_COUNT = 5

# Время отправки (для справки, реальное расписание через launchd)
SEND_TIME = "09:00"

# OpenAI (Whisper)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Instagram Graph API
INSTAGRAM_ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN", "")
INSTAGRAM_BUSINESS_ACCOUNT_ID = os.getenv("INSTAGRAM_BUSINESS_ACCOUNT_ID", "")

# VK (для публикации — user token с правами video,wall)
VK_USER_TOKEN = os.getenv("VK_USER_TOKEN", "")
VK_GROUP_ID = os.getenv("VK_GROUP_ID", "")

# YouTube OAuth2
YOUTUBE_CLIENT_ID = os.getenv("YOUTUBE_CLIENT_ID", "")
YOUTUBE_CLIENT_SECRET = os.getenv("YOUTUBE_CLIENT_SECRET", "")
YOUTUBE_REFRESH_TOKEN = os.getenv("YOUTUBE_REFRESH_TOKEN", "")

# Временное хранилище видео
PROJECT_DIR = Path(__file__).resolve().parent.parent
TEMP_VIDEO_DIR = PROJECT_DIR / "data" / "videos"
