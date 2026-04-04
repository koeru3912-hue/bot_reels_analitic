import os
import logging
import google.generativeai as genai

logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

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
    """Генерирует сценарий через Google Gemini на основе данных видео."""
    if not GEMINI_API_KEY:
        return "⚠️ GEMINI_API_KEY не задан. Генерация недоступна."

    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-2.0-flash-lite")

    prompt = PROMPT_TEMPLATE.format(
        title=item.get("title", "Без названия"),
        platform=item.get("platform", ""),
        views=item.get("views", 0),
        likes=item.get("likes", 0),
    )

    try:
        response = model.generate_content(prompt)
        scenario_text = response.text
    except Exception as e:
        logger.error(f"Ошибка Gemini API: {e}")
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
