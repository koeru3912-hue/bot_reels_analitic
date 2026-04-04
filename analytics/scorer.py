import re

# Слова, которые ДОЛЖНЫ встречаться в заголовке/описании (хотя бы одно)
RELEVANT_WORDS = [
    "ии", "ai", "нейросет", "нейро", "искусственн", "автоматизац",
    "бот", "gpt", "чат-бот", "chatgpt", "администратор",
    "салон", "клиник", "стоматолог", "мед.центр", "медцентр",
    "бизнес", "предприниматель", "crm", "запис", "заявк",
    "маркетинг", "воронк", "лид", "конверси", "продаж",
    "автоответ", "ассистент", "робот", "технолог",
]

# Слова-стоп: если встречаются — точно не наша тема
STOP_WORDS = [
    "рецепт", "кулинар", "готовим", "еда", "блюдо",
    "игра", "game", "roblox", "minecraft", "fortnite",
    "мем", "приколы", "ржака", "смешн",
    "родов", "жену", "муж", "свадьб", "отношени",
    "школьник", "подарок", "сладк",
]


def is_relevant(title: str) -> bool:
    """Проверяет, относится ли контент к нашей нише."""
    title_lower = title.lower()

    # Если есть стоп-слово — отсеиваем
    for word in STOP_WORDS:
        if word in title_lower:
            return False

    # Должно быть хотя бы одно релевантное слово
    for word in RELEVANT_WORDS:
        if word in title_lower:
            return True

    return False


def calculate_score(views: int, likes: int, comments: int, reposts: int) -> float:
    """
    Рассчитывает рейтинг контента.
    Веса: просмотры ×1, лайки ×2, комментарии ×3, репосты ×4
    """
    return views * 1 + likes * 2 + comments * 3 + reposts * 4


def rank_content(items: list[dict]) -> list[dict]:
    """
    Фильтрует по релевантности, сортирует по рейтингу.
    """
    # Сначала фильтруем нерелевантный контент
    relevant = [item for item in items if is_relevant(item.get("title", ""))]

    print(f"   Релевантных: {len(relevant)} из {len(items)}")

    for item in relevant:
        item["score"] = calculate_score(
            item.get("views", 0),
            item.get("likes", 0),
            item.get("comments", 0),
            item.get("reposts", 0),
        )
    return sorted(relevant, key=lambda x: x["score"], reverse=True)
