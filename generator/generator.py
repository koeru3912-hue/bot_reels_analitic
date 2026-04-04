import random
from generator.templates import (
    SCENARIO_TEMPLATE,
    HOOKS,
    PROBLEMS,
    SOLUTIONS,
    PROOFS,
    CTAS,
)


def generate_scenarios(top_items: list[dict]) -> list[str]:
    """
    Генерирует сценарии для топ-контента на основе шаблона.
    """
    scenarios = []
    used_hooks = random.sample(HOOKS, min(len(top_items), len(HOOKS)))
    used_problems = random.sample(PROBLEMS, min(len(top_items), len(PROBLEMS)))
    used_solutions = random.sample(SOLUTIONS, min(len(top_items), len(SOLUTIONS)))
    used_proofs = random.sample(PROOFS, min(len(top_items), len(PROOFS)))
    used_ctas = random.sample(CTAS, min(len(top_items), len(CTAS)))

    for i, item in enumerate(top_items):
        scenario = SCENARIO_TEMPLATE.format(
            number=i + 1,
            title=item.get("title", "Без названия"),
            platform=item.get("platform", ""),
            url=item.get("url", "#"),
            score=item.get("score", 0),
            views=item.get("views", 0),
            likes=item.get("likes", 0),
            comments=item.get("comments", 0),
            reposts=item.get("reposts", 0),
            hook=used_hooks[i],
            problem=used_problems[i],
            solution=used_solutions[i],
            proof=used_proofs[i],
            cta=used_ctas[i],
        )
        scenarios.append(scenario)

    return scenarios


def format_daily_message(scenarios: list[str]) -> str:
    """
    Формирует итоговое сообщение для отправки в Telegram.
    """
    header = "🔥 *Топ-5 идей для Reels на сегодня*\n\n"
    return header + "\n".join(scenarios)
