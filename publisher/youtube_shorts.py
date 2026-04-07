import logging
from typing import Optional
from pathlib import Path
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from config.settings import (
    YOUTUBE_CLIENT_ID,
    YOUTUBE_CLIENT_SECRET,
    YOUTUBE_REFRESH_TOKEN,
)

logger = logging.getLogger(__name__)

TOKEN_URI = "https://oauth2.googleapis.com/token"


def _get_youtube_client():
    """Создаёт авторизованный YouTube API клиент."""
    if not all([YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET, YOUTUBE_REFRESH_TOKEN]):
        raise ValueError("YouTube OAuth2 credentials не заданы")

    credentials = Credentials(
        token=None,
        refresh_token=YOUTUBE_REFRESH_TOKEN,
        client_id=YOUTUBE_CLIENT_ID,
        client_secret=YOUTUBE_CLIENT_SECRET,
        token_uri=TOKEN_URI,
    )

    return build("youtube", "v3", credentials=credentials)


def publish_to_youtube(
    video_path: str,
    title: str,
    description: str,
    hashtags: str,
    srt_path: Optional[str] = None,
) -> dict:
    """
    Загружает видео на YouTube как Short.
    Опционально загружает SRT-субтитры.
    Возвращает dict с video_id и url.
    """
    youtube = _get_youtube_client()

    # Добавляем #Shorts в title для алгоритма YouTube
    if "#Shorts" not in title and "#shorts" not in title:
        title = f"{title} #Shorts"

    full_description = f"{description}\n\n{hashtags}" if hashtags else description
    tags = [tag.strip("#") for tag in hashtags.split() if tag.startswith("#")]

    body = {
        "snippet": {
            "title": title[:100],
            "description": full_description,
            "tags": tags[:30],
            "categoryId": "22",  # People & Blogs
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False,
        },
    }

    media = MediaFileUpload(video_path, mimetype="video/mp4", resumable=True)

    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media,
    )
    response = request.execute()
    video_id = response["id"]

    logger.info(f"YouTube Short загружен: {video_id}")

    # Загружаем SRT-субтитры если есть
    if srt_path and Path(srt_path).exists():
        try:
            youtube.captions().insert(
                part="snippet",
                body={
                    "snippet": {
                        "videoId": video_id,
                        "language": "ru",
                        "name": "Русские субтитры",
                    }
                },
                media_body=MediaFileUpload(srt_path, mimetype="application/x-subrip"),
            ).execute()
            logger.info(f"SRT субтитры загружены для {video_id}")
        except Exception as e:
            logger.warning(f"Не удалось загрузить субтитры: {e}")

    return {
        "video_id": video_id,
        "url": f"https://youtube.com/shorts/{video_id}",
    }
