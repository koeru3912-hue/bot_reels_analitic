"""Мониторинг конкурентных Telegram-каналов через публичный веб-просмотр."""

import json
import logging
import re
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
COMPETITORS_FILE = DATA_DIR / "competitors.json"
COMPETITOR_POSTS_FILE = DATA_DIR / "competitor_posts.json"


def _load_competitors() -> list[str]:
    """Загружает список каналов конкурентов."""
    if not COMPETITORS_FILE.exists():
        return []
    try:
        with open(COMPETITORS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def save_competitors(channels: list[str]):
    """Сохраняет список каналов конкурентов."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    # Нормализуем: убираем @ и https://t.me/
    clean = []
    for ch in channels:
        ch = ch.strip().lstrip("@")
        ch = re.sub(r"https?://t\.me/", "", ch)
        ch = ch.strip("/")
        if ch:
            clean.append(ch)
    with open(COMPETITORS_FILE, "w", encoding="utf-8") as f:
        json.dump(clean, f, ensure_ascii=False, indent=2)


def add_competitor(channel: str) -> str:
    """Добавляет конкурента. Возвращает нормализованное имя."""
    channel = channel.strip().lstrip("@")
    channel = re.sub(r"https?://t\.me/", "", channel)
    channel = channel.strip("/")

    competitors = _load_competitors()
    if channel in competitors:
        return channel
    competitors.append(channel)
    save_competitors(competitors)
    return channel


def remove_competitor(channel: str) -> bool:
    """Удаляет конкурента. Возвращает True если был удалён."""
    channel = channel.strip().lstrip("@")
    channel = re.sub(r"https?://t\.me/", "", channel)
    channel = channel.strip("/")

    competitors = _load_competitors()
    if channel not in competitors:
        return False
    competitors.remove(channel)
    save_competitors(competitors)
    return True


def get_competitors() -> list[str]:
    """Возвращает список конкурентов."""
    return _load_competitors()


def fetch_channel_posts(channel: str, limit: int = 10) -> list[dict]:
    """
    Парсит последние посты из публичного веб-просмотра Telegram-канала.
    Возвращает список dict с полями: text, views, date, url, reactions.
    """
    url = f"https://t.me/s/{channel}"
    try:
        resp = requests.get(url, timeout=15, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
        })
        resp.raise_for_status()
    except Exception as e:
        logger.error(f"Ошибка загрузки канала {channel}: {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    posts = []

    for wrap in soup.select("div.tgme_widget_message_wrap"):
        msg = wrap.select_one("div.tgme_widget_message")
        if not msg:
            continue

        # Текст поста
        text_el = wrap.select_one("div.tgme_widget_message_text")
        text = text_el.get_text(separator="\n").strip() if text_el else ""
        if not text:
            continue

        # Просмотры
        views_el = wrap.select_one("span.tgme_widget_message_views")
        views_str = views_el.text.strip() if views_el else "0"
        views = _parse_views(views_str)

        # Дата
        time_el = wrap.select_one("time.time")
        date_str = time_el["datetime"] if time_el and time_el.has_attr("datetime") else ""

        # URL поста
        link_el = wrap.select_one("a.tgme_widget_message_date")
        post_url = link_el["href"] if link_el and link_el.has_attr("href") else ""

        # Реакции
        reactions = []
        for reaction in wrap.select("span.tgme_reaction"):
            emoji_el = reaction.select_one("b")
            emoji = emoji_el.text if emoji_el else ""
            count_text = reaction.get_text().strip()
            # Убираем текст эмодзи, оставляем число
            count_str = re.sub(r"[^\d]", "", count_text.replace(emoji, ""))
            count = int(count_str) if count_str else 0
            if emoji or count:
                reactions.append({"emoji": emoji, "count": count})

        posts.append({
            "channel": channel,
            "text": text[:500],
            "views": views,
            "date": date_str,
            "url": post_url,
            "reactions": reactions,
        })

    # Берём последние N постов (на странице они в хронологическом порядке)
    return posts[-limit:]


def _parse_views(s: str) -> int:
    """Парсит строку просмотров: '1.2K' -> 1200, '3.5M' -> 3500000."""
    s = s.strip().upper()
    if "K" in s:
        return int(float(s.replace("K", "")) * 1000)
    if "M" in s:
        return int(float(s.replace("M", "")) * 1000000)
    try:
        return int(s)
    except ValueError:
        return 0


def fetch_all_competitors(limit_per_channel: int = 5) -> list[dict]:
    """Собирает посты всех конкурентов."""
    competitors = _load_competitors()
    all_posts = []
    for ch in competitors:
        posts = fetch_channel_posts(ch, limit=limit_per_channel)
        all_posts.extend(posts)
    return all_posts


def get_competitor_report() -> str:
    """Формирует отчёт по последним постам конкурентов."""
    competitors = _load_competitors()
    if not competitors:
        return "🔍 Список конкурентов пуст.\n\nДобавьте каналы кнопкой ниже."

    lines = [f"🔍 *Мониторинг конкурентов* ({len(competitors)} каналов)\n"]

    for ch in competitors:
        posts = fetch_channel_posts(ch, limit=3)
        lines.append(f"\n📢 *@{ch}* — последние посты:")

        if not posts:
            lines.append("  ⚠️ Не удалось загрузить")
            continue

        for i, post in enumerate(posts, 1):
            text_preview = post["text"][:80].replace("\n", " ")
            views = post["views"]
            total_reactions = sum(r["count"] for r in post.get("reactions", []))
            lines.append(
                f"  {i}. {text_preview}..."
                f"\n     👁 {views:,} | ❤️ {total_reactions}"
            )

    return "\n".join(lines)
