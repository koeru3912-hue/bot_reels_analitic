import os
import requests
from config.keywords import KEYWORDS

# Instagram не имеет публичного API для поиска Reels.
# Используем RapidAPI сервис для скрапинга.
RAPIDAPI_KEY = ""
RAPIDAPI_HOST = "instagram-scraper-api2.p.rapidapi.com"
SEARCH_URL = f"https://{RAPIDAPI_HOST}/v1/hashtag"


def fetch_instagram_reels() -> list[dict]:
    """
    Ищет Instagram Reels по хештегам через RapidAPI.
    """
    api_key = os.getenv("RAPIDAPI_KEY", RAPIDAPI_KEY)

    if not api_key:
        print("[Instagram] RapidAPI ключ не задан, пропускаю")
        return []

    all_reels = []

    # Преобразуем ключевые слова в хештеги
    hashtags = ["ии_для_бизнеса", "нейросети", "ai_администратор", "автоматизация_бизнеса"]

    for tag in hashtags:
        headers = {
            "X-RapidAPI-Key": api_key,
            "X-RapidAPI-Host": RAPIDAPI_HOST,
        }
        params = {"hashtag": tag}

        try:
            resp = requests.get(SEARCH_URL, headers=headers, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"[Instagram] Ошибка поиска по #{tag}: {e}")
            continue

        for item in data.get("data", {}).get("items", [])[:5]:
            all_reels.append({
                "title": (item.get("caption", {}) or {}).get("text", "")[:100],
                "url": f"https://www.instagram.com/reel/{item.get('code', '')}",
                "platform": "Instagram",
                "views": int(item.get("play_count", 0) or item.get("view_count", 0) or 0),
                "likes": int(item.get("like_count", 0)),
                "comments": int(item.get("comment_count", 0)),
                "reposts": int(item.get("reshare_count", 0) or 0),
            })

    print(f"[Instagram] Найдено {len(all_reels)} reels")
    return all_reels
