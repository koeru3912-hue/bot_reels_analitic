import logging
from typing import Optional
from pathlib import Path
from openai import AsyncOpenAI
from config.settings import OPENAI_API_KEY

logger = logging.getLogger(__name__)

client = AsyncOpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None


async def generate_srt(video_path: str, language: str = "ru") -> Optional[str]:
    """
    Отправляет видео в OpenAI Whisper API, возвращает SRT-субтитры.
    Также сохраняет .srt файл рядом с видео.
    """
    if not client:
        logger.error("OPENAI_API_KEY не задан — субтитры недоступны")
        return None

    video = Path(video_path)
    if not video.exists():
        logger.error(f"Файл не найден: {video_path}")
        return None

    try:
        with open(video, "rb") as f:
            response = await client.audio.transcriptions.create(
                model="whisper-1",
                file=f,
                response_format="srt",
                language=language,
            )

        srt_content = response
        srt_path = video.with_suffix(".srt")
        srt_path.write_text(srt_content, encoding="utf-8")
        logger.info(f"SRT сохранён: {srt_path}")

        return srt_content

    except Exception as e:
        logger.error(f"Ошибка Whisper API: {e}")
        return None
