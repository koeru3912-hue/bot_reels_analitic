"""Трекинг опубликованных постов и аналитика канала."""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
POSTS_LOG_FILE = DATA_DIR / "published_posts.json"


def _load_posts_log() -> list[dict]:
    if not POSTS_LOG_FILE.exists():
        return []
    try:
        with open(POSTS_LOG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def _save_posts_log(posts: list[dict]):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(POSTS_LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(posts, f, ensure_ascii=False, indent=2)


def log_published_post(
    text: str,
    platforms: list[str],
    has_media: bool = False,
    media_type: str = "",
):
    """Записывает опубликованный пост в лог."""
    posts = _load_posts_log()
    posts.append({
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "text_preview": text[:100],
        "text_length": len(text),
        "platforms": platforms,
        "has_media": has_media,
        "media_type": media_type,
    })

    # Храним максимум 365 дней
    cutoff = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
    posts = [p for p in posts if p.get("date", "") >= cutoff]

    _save_posts_log(posts)


def get_weekly_report() -> str:
    """Формирует еженедельный отчёт по активности."""
    posts = _load_posts_log()

    week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    month_ago = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

    week_posts = [p for p in posts if p.get("date", "") >= week_ago]
    month_posts = [p for p in posts if p.get("date", "") >= month_ago]
    total_posts = len(posts)

    # Статистика за неделю
    week_count = len(week_posts)
    week_with_media = sum(1 for p in week_posts if p.get("has_media"))
    week_platforms = {}
    for p in week_posts:
        for platform in p.get("platforms", []):
            week_platforms[platform] = week_platforms.get(platform, 0) + 1

    # Средняя длина поста
    avg_length = 0
    if week_posts:
        avg_length = sum(p.get("text_length", 0) for p in week_posts) // len(week_posts)

    # Сравнение с прошлой неделей
    two_weeks_ago = (datetime.now() - timedelta(days=14)).strftime("%Y-%m-%d")
    prev_week_posts = [p for p in posts if two_weeks_ago <= p.get("date", "") < week_ago]
    prev_count = len(prev_week_posts)

    if prev_count > 0:
        change = ((week_count - prev_count) / prev_count) * 100
        trend = f"📈 +{change:.0f}%" if change > 0 else f"📉 {change:.0f}%"
    elif week_count > 0:
        trend = "📈 первая неделя"
    else:
        trend = "—"

    lines = [
        "📊 *Еженедельный отчёт*\n",
        f"📅 Период: последние 7 дней\n",
        f"✍️ Постов опубликовано: *{week_count}*",
        f"📎 Из них с медиа: {week_with_media}",
        f"📏 Средняя длина поста: {avg_length} символов",
        f"📈 Динамика: {trend}",
    ]

    if week_platforms:
        lines.append("\n📡 *По площадкам:*")
        for platform, count in sorted(week_platforms.items()):
            lines.append(f"  • {platform}: {count}")

    lines.append(f"\n📆 За месяц: {len(month_posts)} постов")
    lines.append(f"📋 Всего за всё время: {total_posts}")

    # Рекомендации
    lines.append("\n💡 *Рекомендации:*")
    if week_count == 0:
        lines.append("  ⚠️ На этой неделе не было постов. Регулярность — ключ к росту!")
    elif week_count < 3:
        lines.append("  📌 Попробуйте публиковать хотя бы 3-4 раза в неделю")
    elif week_count >= 5:
        lines.append("  🔥 Отличная активность! Поддерживайте темп")

    if week_posts and week_with_media / max(week_count, 1) < 0.3:
        lines.append("  📸 Добавляйте медиа — посты с фото/видео получают больше охвата")

    return "\n".join(lines)
