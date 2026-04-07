import logging
import requests
from pathlib import Path
from config.settings import VK_USER_TOKEN, VK_GROUP_ID

logger = logging.getLogger(__name__)

VK_API_URL = "https://api.vk.com/method"
VK_API_VERSION = "5.199"


def publish_to_vk(
    video_path: str,
    title: str,
    description: str,
    hashtags: str,
) -> dict:
    """
    Публикует видео как VK Clip.
    Возвращает dict с video_id и owner_id при успехе.
    Бросает Exception при ошибке.
    """
    if not VK_USER_TOKEN:
        raise ValueError("VK_USER_TOKEN не задан")

    full_description = f"{description}\n\n{hashtags}" if hashtags else description

    # Шаг 1: получить URL для загрузки
    params = {
        "name": title,
        "description": full_description,
        "is_private": 0,
        "wallpost": 1,
        "clip": 1,
        "repeat": 1,
        "access_token": VK_USER_TOKEN,
        "v": VK_API_VERSION,
    }
    if VK_GROUP_ID:
        params["group_id"] = VK_GROUP_ID

    resp = requests.post(f"{VK_API_URL}/video.save", data=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    if "error" in data:
        raise ValueError(f"VK API error: {data['error'].get('error_msg', data['error'])}")

    upload_url = data["response"]["upload_url"]
    video_id = data["response"].get("video_id")
    owner_id = data["response"].get("owner_id")

    # Шаг 2: загрузить видео
    path = Path(video_path)
    with open(path, "rb") as f:
        upload_resp = requests.post(
            upload_url,
            files={"video_file": (path.name, f, "video/mp4")},
            timeout=300,
        )
        upload_resp.raise_for_status()

    logger.info(f"VK Clip опубликован: video_id={video_id}, owner_id={owner_id}")

    return {
        "video_id": video_id,
        "owner_id": owner_id,
        "url": f"https://vk.com/clip{owner_id}_{video_id}",
    }
