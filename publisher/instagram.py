import time
import logging
from typing import Optional
import requests
from config.settings import INSTAGRAM_ACCESS_TOKEN, INSTAGRAM_BUSINESS_ACCOUNT_ID

logger = logging.getLogger(__name__)

GRAPH_API_URL = "https://graph.instagram.com/v22.0"
POLL_INTERVAL = 5  # секунд
POLL_TIMEOUT = 120  # максимум секунд ожидания


def publish_to_instagram(
    video_public_url: str,
    caption: str,
    cover_public_url: Optional[str] = None,
) -> dict:
    """
    Публикует Reels в Instagram через Graph API.
    Требует публичный URL видео (загрузить через storage.py).
    Возвращает dict с media_id при успехе.
    """
    if not INSTAGRAM_ACCESS_TOKEN or not INSTAGRAM_BUSINESS_ACCOUNT_ID:
        raise ValueError("Instagram credentials не заданы")

    ig_id = INSTAGRAM_BUSINESS_ACCOUNT_ID

    # Шаг 1: создать media container
    params = {
        "media_type": "REELS",
        "video_url": video_public_url,
        "caption": caption,
        "access_token": INSTAGRAM_ACCESS_TOKEN,
    }
    if cover_public_url:
        params["cover_url"] = cover_public_url

    resp = requests.post(f"{GRAPH_API_URL}/{ig_id}/media", data=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    if "id" not in data:
        raise ValueError(f"Instagram API error: {data}")

    container_id = data["id"]
    logger.info(f"Instagram container создан: {container_id}")

    # Шаг 2: ждём обработки видео
    elapsed = 0
    while elapsed < POLL_TIMEOUT:
        time.sleep(POLL_INTERVAL)
        elapsed += POLL_INTERVAL

        status_resp = requests.get(
            f"{GRAPH_API_URL}/{container_id}",
            params={
                "fields": "status_code",
                "access_token": INSTAGRAM_ACCESS_TOKEN,
            },
            timeout=15,
        )
        status_resp.raise_for_status()
        status_data = status_resp.json()
        status_code = status_data.get("status_code", "")

        if status_code == "FINISHED":
            break
        elif status_code == "ERROR":
            raise ValueError(f"Instagram обработка видео завершилась ошибкой: {status_data}")

        logger.info(f"Instagram обработка... ({elapsed}с, статус: {status_code})")
    else:
        raise TimeoutError(f"Instagram: таймаут обработки видео ({POLL_TIMEOUT}с)")

    # Шаг 3: опубликовать
    publish_resp = requests.post(
        f"{GRAPH_API_URL}/{ig_id}/media_publish",
        data={
            "creation_id": container_id,
            "access_token": INSTAGRAM_ACCESS_TOKEN,
        },
        timeout=30,
    )
    publish_resp.raise_for_status()
    publish_data = publish_resp.json()

    if "id" not in publish_data:
        raise ValueError(f"Instagram publish error: {publish_data}")

    media_id = publish_data["id"]
    logger.info(f"Instagram Reels опубликован: {media_id}")

    return {
        "media_id": media_id,
    }
