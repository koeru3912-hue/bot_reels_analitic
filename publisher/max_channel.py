import logging
import time
import requests

from config.settings import MAX_BOT_TOKEN, MAX_CHAT_ID

logger = logging.getLogger(__name__)

MAX_API_URL = "https://platform-api.max.ru"


def _upload_image(photo_path: str) -> dict:
    """Загружает изображение в Max и возвращает payload для attachment."""
    headers = {"Authorization": MAX_BOT_TOKEN}

    # 1. Получить upload URL
    resp = requests.post(
        f"{MAX_API_URL}/uploads",
        params={"type": "image"},
        headers=headers,
        timeout=30,
    )
    resp.raise_for_status()
    upload_url = resp.json()["url"]

    # 2. Загрузить файл
    with open(photo_path, "rb") as f:
        upload_resp = requests.post(
            upload_url,
            files={"data": f},
            timeout=60,
        )
    upload_resp.raise_for_status()
    data = upload_resp.json()

    # 3. Извлечь token из ответа {"photos": {"id": {"token": "..."}}}
    photos = data.get("photos", {})
    for photo_id, photo_data in photos.items():
        token = photo_data.get("token", "")
        if token:
            return {"token": token}

    raise ValueError(f"Не удалось получить token фото: {data}")


def publish_to_max(text: str, photo_path: str = None) -> dict:
    """
    Публикует сообщение в канал Max.
    Опционально прикрепляет фото.
    Возвращает dict с message_id.
    """
    if not MAX_BOT_TOKEN:
        raise ValueError("MAX_BOT_TOKEN не задан в .env")
    if not MAX_CHAT_ID:
        raise ValueError("MAX_CHAT_ID не задан в .env")

    headers = {
        "Authorization": MAX_BOT_TOKEN,
        "Content-Type": "application/json",
    }

    body = {
        "text": text[:4000],
        "notify": True,
    }

    # Прикрепить фото если есть
    if photo_path:
        try:
            photo_payload = _upload_image(photo_path)
            body["attachments"] = [
                {
                    "type": "image",
                    "payload": photo_payload,
                }
            ]
        except Exception as e:
            logger.warning(f"Не удалось загрузить фото в Max: {e}")

    resp = requests.post(
        f"{MAX_API_URL}/messages",
        params={"chat_id": MAX_CHAT_ID},
        headers=headers,
        json=body,
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()

    msg_id = data.get("message", {}).get("body", {}).get("mid", "")
    logger.info(f"Max пост опубликован: message_id={msg_id}")

    return {"message_id": msg_id}
