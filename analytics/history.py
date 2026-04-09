"""Хранение истории топ-контента и дедупликация."""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

HISTORY_FILE = Path(__file__).resolve().parent.parent / "data" / "history.json"
DEDUP_DAYS = 7  # не показывать повторы за последние N дней


def _load_history() -> list[dict]:
    """Загружает историю из файла."""
    if not HISTORY_FILE.exists():
        return []
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def _save_history(history: list[dict]):
    """Сохраняет историю в файл."""
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def get_seen_urls(days: int = DEDUP_DAYS) -> set[str]:
    """Возвращает набор URL, которые были в топах за последние N дней."""
    history = _load_history()
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    seen = set()
    for entry in history:
        if entry.get("date", "") >= cutoff:
            for item in entry.get("items", []):
                url = item.get("url", "")
                if url:
                    seen.add(url)
    return seen


def save_daily_top(items: list[dict]):
    """Сохраняет текущий топ в историю (с датой)."""
    history = _load_history()

    today = datetime.now().strftime("%Y-%m-%d")

    # Обновляем запись за сегодня если уже есть
    for entry in history:
        if entry["date"] == today:
            entry["items"] = items
            _save_history(history)
            return

    history.append({
        "date": today,
        "items": items,
    })

    # Храним максимум 90 дней
    cutoff = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
    history = [e for e in history if e.get("date", "") >= cutoff]

    _save_history(history)


def deduplicate(items: list[dict]) -> list[dict]:
    """Убирает из списка контент, который уже был в топах за последние N дней."""
    seen = get_seen_urls()
    if not seen:
        return items

    original_count = len(items)
    filtered = [item for item in items if item.get("url", "") not in seen]

    removed = original_count - len(filtered)
    if removed:
        logger.info(f"Дедупликация: убрано {removed} повторов из {original_count}")

    return filtered


def get_history_summary(days: int = 7) -> str:
    """Формирует текстовую сводку истории за N дней."""
    history = _load_history()
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    recent = [e for e in history if e.get("date", "") >= cutoff]
    recent.sort(key=lambda x: x["date"], reverse=True)

    if not recent:
        return "📊 История пуста — данных пока нет."

    lines = [f"📊 *История топов за {days} дней*\n"]

    for entry in recent:
        date = entry["date"]
        items = entry.get("items", [])
        lines.append(f"\n📅 *{date}* ({len(items)} шт.)")

        for i, item in enumerate(items[:5], 1):
            title = item.get("title", "—")[:50]
            views = item.get("views", 0)
            platform = item.get("platform", "")
            lines.append(f"  {i}. {title} ({platform}, 👁 {views:,})")

    total_items = sum(len(e.get("items", [])) for e in recent)
    lines.append(f"\n📈 Всего уникальных идей: {total_items}")

    return "\n".join(lines)
