import os
import logging
import requests

logger = logging.getLogger(__name__)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

PROMPT_TEMPLATE = """Ты — эксперт по созданию коротких вертикальных видео (Reels/Shorts/TikTok).

На основе заголовка видео напиши сценарий для Reels длительностью 30 секунд.

Заголовок: {title}
Платформа: {platform}
Просмотры: {views:,} | Лайки: {likes:,}

Напиши сценарий строго в таком формате:

🎯 Сценарий:

1. Хук (0-3 сек):
[Цепляющая фраза по теме видео]

2. Проблема (3-7 сек):
[Описание проблемы, которую решает видео]

3. Решение (7-20 сек):
[Конкретное решение по теме заголовка]

4. Доказательство (20-25 сек):
[Факт или кейс, подтверждающий решение]

5. CTA (25-30 сек):
[Призыв к действию]

Пиши на русском, кратко и энергично. Сценарий должен точно соответствовать теме заголовка."""


def generate_scenario(item: dict) -> str:
    """Генерирует сценарий через OpenRouter на основе данных видео."""
    if not OPENROUTER_API_KEY:
        return "⚠️ OPENROUTER_API_KEY не задан. Генерация недоступна."

    prompt = PROMPT_TEMPLATE.format(
        title=item.get("title", "Без названия"),
        platform=item.get("platform", ""),
        views=item.get("views", 0),
        likes=item.get("likes", 0),
    )

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": "google/gemma-3-4b-it:free",
        "messages": [{"role": "user", "content": prompt}],
    }

    try:
        resp = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=120)
        resp.raise_for_status()
        data = resp.json()
        scenario_text = data["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"Ошибка OpenRouter API: {e}")
        return f"⚠️ Ошибка генерации сценария: {e}"

    title = item.get("title", "Без названия")
    url = item.get("url", "#")
    platform = item.get("platform", "")
    views = item.get("views", 0)
    likes = item.get("likes", 0)
    comments = item.get("comments", 0)

    header = (
        f"🎬 *Сценарий*\n\n"
        f"📌 *Заголовок:* [{title}]({url})\n"
        f"📊 {platform} | 👁 {views:,} | ❤️ {likes:,} | 💬 {comments:,}\n\n"
        f"---\n\n"
    )

    return header + scenario_text
