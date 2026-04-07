import logging
from typing import Optional
import requests
from pathlib import Path

logger = logging.getLogger(__name__)

UPLOAD_URL = "https://0x0.st"


def upload_to_public_url(file_path: str) -> Optional[str]:
    """
    Загружает файл на публичный хостинг (0x0.st).
    Возвращает публичный URL или None при ошибке.
    Нужно для Instagram Graph API, который требует публичный URL видео.
    """
    path = Path(file_path)
    if not path.exists():
        logger.error(f"Файл не найден: {file_path}")
        return None

    try:
        with open(path, "rb") as f:
            resp = requests.post(
                UPLOAD_URL,
                files={"file": (path.name, f)},
                timeout=120,
            )
            resp.raise_for_status()

        public_url = resp.text.strip()
        logger.info(f"Файл загружен: {public_url}")
        return public_url

    except Exception as e:
        logger.error(f"Ошибка загрузки на {UPLOAD_URL}: {e}")
        return None
