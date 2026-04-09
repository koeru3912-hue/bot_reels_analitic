import logging

from openai import OpenAI

from config.settings import OPENAI_API_KEY

logger = logging.getLogger(__name__)

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
    """Генерирует сценарий через OpenAI API на основе данных видео."""
    if not OPENAI_API_KEY:
        return "⚠️ OPENAI_API_KEY не задан. Генерация недоступна."

    prompt = PROMPT_TEMPLATE.format(
        title=item.get("title", "Без названия"),
        platform=item.get("platform", ""),
        views=item.get("views", 0),
        likes=item.get("likes", 0),
    )

    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
        )
        scenario_text = response.choices[0].message.content
    except Exception as e:
        logger.error(f"Ошибка OpenAI API: {e}")
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


HOOKS_PROMPT = """Ты — эксперт по коротким видео (Reels/Shorts/TikTok) и вирусным хукам.

Вот заголовки топовых видео в нише AI/автоматизация для бизнеса:

{titles_block}

## Задача:

Проанализируй эти заголовки и дай практический разбор хуков.

1. ПАТТЕРНЫ ХУКОВ
Выдели 3-4 паттерна, которые используются в этих заголовках. Для каждого:
- Название паттерна (например: "Шок-цифра", "Провокационный вопрос", "Личная история")
- Почему это работает (1 предложение)
- Пример из списка выше

2. ФОРМУЛЫ ХУКОВ ДЛЯ ВАШИХ КЛИПОВ
Напиши 5 готовых хуков (первые 3 секунды видео), которые можно использовать прямо сейчас.
Тематика: AI-автоматизация, чат-боты, нейросети для бизнеса, запись клиентов.
Формат: текст + [действие на экране]

3. АНТИПАТТЕРНЫ
Чего избегать в хуках (2-3 пункта).

Пиши кратко, по делу, на русском."""


def generate_hooks_analysis(items: list[dict]) -> str:
    """Генерирует анализ хуков на основе топовых видео."""
    if not OPENAI_API_KEY:
        return "⚠️ OPENAI_API_KEY не задан."

    titles_block = "\n".join(
        f"- {item.get('title', '')} (👁 {item.get('views', 0):,})"
        for item in items
    )

    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": HOOKS_PROMPT.format(titles_block=titles_block)}],
        )
        return "🎣 *Анализ хуков*\n\n" + response.choices[0].message.content
    except Exception as e:
        logger.error(f"Ошибка анализа хуков: {e}")
        return f"⚠️ Ошибка: {e}"
