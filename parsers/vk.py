import os
import requests
from config.keywords import KEYWORDS

VK_TOKEN = os.getenv("VK_TOKEN", "")
VK_API_VERSION = "5.199"
SEARCH_URL = "https://api.vk.com/method/video.search"


def fetch_vk_clips() -> list[dict]:
    """
    Ищет VK Клипы по ключевым словам через VK API.
    """
    if not VK_TOKEN:
        print("[VK] Токен не задан, пропускаю")
        return []

    all_clips = []

    for keyword in KEYWORDS[:4]:
        params = {
            "q": keyword,
            "count": 5,
            "sort": 2,  # по популярности
            "filters": "short",
            "access_token": VK_TOKEN,
            "v": VK_API_VERSION,
        }

        try:
            resp = requests.get(SEARCH_URL, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"[VK] Ошибка поиска по '{keyword}': {e}")
            continue

        if "error" in data:
            print(f"[VK] API ошибка: {data['error'].get('error_msg', '')}")
            continue

        for item in data.get("response", {}).get("items", []):
            owner_id = item.get("owner_id", 0)
            video_id = item.get("id", 0)
            all_clips.append({
                "title": item.get("title", ""),
                "url": f"https://vk.com/video{owner_id}_{video_id}",
                "platform": "VK",
                "views": int(item.get("views", 0)),
                "likes": int(item.get("likes", {}).get("count", 0)),
                "comments": int(item.get("comments", 0)),
                "reposts": int(item.get("reposts", {}).get("count", 0)),
            })

    print(f"[VK] Найдено {len(all_clips)} клипов")
    return all_clips
