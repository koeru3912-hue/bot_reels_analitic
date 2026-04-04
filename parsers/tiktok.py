import requests
from config.keywords import KEYWORDS

# TikTok не имеет простого публичного API для поиска.
# Используем неофициальный подход через веб-скрапинг.
# Для продакшена рекомендуется TikTok Research API или сервис типа Apify.

RAPIDAPI_KEY = ""  # Установите ключ RapidAPI если используете сторонний сервис
RAPIDAPI_HOST = "tiktok-scraper7.p.rapidapi.com"
SEARCH_URL = f"https://{RAPIDAPI_HOST}/feed/search"


def fetch_tiktok_videos() -> list[dict]:
    """
    Ищет TikTok видео по ключевым словам через RapidAPI.
    """
    import os
    api_key = os.getenv("RAPIDAPI_KEY", RAPIDAPI_KEY)

    if not api_key:
        print("[TikTok] RapidAPI ключ не задан, пропускаю")
        return []

    all_videos = []

    for keyword in KEYWORDS[:4]:
        headers = {
            "X-RapidAPI-Key": api_key,
            "X-RapidAPI-Host": RAPIDAPI_HOST,
        }
        params = {
            "keywords": keyword,
            "count": "5",
            "cursor": "0",
            "region": "RU",
        }

        try:
            resp = requests.get(SEARCH_URL, headers=headers, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"[TikTok] Ошибка поиска по '{keyword}': {e}")
            continue

        for item in data.get("data", {}).get("videos", []):
            stats = item.get("stats", {})
            all_videos.append({
                "title": item.get("desc", ""),
                "url": f"https://www.tiktok.com/@{item.get('author', {}).get('uniqueId', '')}/video/{item.get('id', '')}",
                "platform": "TikTok",
                "views": int(stats.get("playCount", 0)),
                "likes": int(stats.get("diggCount", 0)),
                "comments": int(stats.get("commentCount", 0)),
                "reposts": int(stats.get("shareCount", 0)),
            })

    print(f"[TikTok] Найдено {len(all_videos)} видео")
    return all_videos
