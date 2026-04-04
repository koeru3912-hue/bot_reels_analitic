import os
import requests
from config.keywords import KEYWORDS

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")
SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"


def fetch_youtube_shorts() -> list[dict]:
    """
    Ищет YouTube Shorts по ключевым словам и возвращает список с метриками.
    """
    if not YOUTUBE_API_KEY:
        print("[YouTube] API ключ не задан, пропускаю")
        return []

    all_videos = []

    for keyword in KEYWORDS[:4]:  # Берём первые 4 ключевых слова чтобы не тратить квоту
        params = {
            "part": "snippet",
            "q": keyword + " #shorts",
            "type": "video",
            "videoDuration": "short",
            "order": "viewCount",
            "maxResults": 5,
            "key": YOUTUBE_API_KEY,
        }

        try:
            resp = requests.get(SEARCH_URL, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"[YouTube] Ошибка поиска по '{keyword}': {e}")
            continue

        video_ids = [item["id"]["videoId"] for item in data.get("items", [])]
        if not video_ids:
            continue

        # Получаем статистику видео
        stats_params = {
            "part": "statistics,snippet",
            "id": ",".join(video_ids),
            "key": YOUTUBE_API_KEY,
        }

        try:
            stats_resp = requests.get(VIDEOS_URL, params=stats_params, timeout=10)
            stats_resp.raise_for_status()
            stats_data = stats_resp.json()
        except Exception as e:
            print(f"[YouTube] Ошибка получения статистики: {e}")
            continue

        for item in stats_data.get("items", []):
            stats = item.get("statistics", {})
            snippet = item.get("snippet", {})
            all_videos.append({
                "title": snippet.get("title", ""),
                "url": f"https://youtube.com/shorts/{item['id']}",
                "platform": "YouTube",
                "views": int(stats.get("viewCount", 0)),
                "likes": int(stats.get("likeCount", 0)),
                "comments": int(stats.get("commentCount", 0)),
                "reposts": 0,  # YouTube API не отдаёт репосты
            })

    print(f"[YouTube] Найдено {len(all_videos)} видео")
    return all_videos
