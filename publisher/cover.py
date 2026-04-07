import asyncio
import logging
from typing import Optional
from pathlib import Path

logger = logging.getLogger(__name__)


async def extract_cover(video_path: str, timestamp: str = "00:00:01") -> Optional[str]:
    """
    Извлекает кадр из видео через ffmpeg и сохраняет как cover.jpg.
    Возвращает путь к файлу обложки или None при ошибке.
    """
    video = Path(video_path)
    cover_path = video.with_name(video.stem + "_cover.jpg")

    try:
        process = await asyncio.create_subprocess_exec(
            "ffmpeg", "-y",
            "-i", str(video),
            "-ss", timestamp,
            "-vframes", "1",
            "-q:v", "2",
            str(cover_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await process.communicate()

        if process.returncode != 0:
            logger.error(f"ffmpeg ошибка: {stderr.decode()}")
            return None

        if cover_path.exists():
            logger.info(f"Обложка сохранена: {cover_path}")
            return str(cover_path)

        return None

    except FileNotFoundError:
        logger.error("ffmpeg не найден. Установите ffmpeg для извлечения обложек.")
        return None
    except Exception as e:
        logger.error(f"Ошибка извлечения обложки: {e}")
        return None
