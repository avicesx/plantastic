import logging
import os
from .base import RecognitionGateway
from .remote import RemoteGateway

logger = logging.getLogger(__name__)

DEFAULT_MODE = "legacy"
DEFAULT_RECOGNITION_URL = "http://recognition:8003"
DEFAULT_TIMEOUT = 10.0


def create_gateway() -> RecognitionGateway:
    mode = os.getenv("RECOGNITION_MODE", DEFAULT_MODE).strip().lower()

    if mode == "legacy":
        # Импорт здесь, чтобы в режиме remote не загружать torch и старый детектор
        from .legacy import LegacyGateway

        logger.info("Распознавание: режим legacy (детектор в backend + контейнеры classifier и disease)")
        return LegacyGateway()

    if mode == "remote":
        url = os.getenv("RECOGNITION_URL", DEFAULT_RECOGNITION_URL)
        timeout = float(os.getenv("RECOGNITION_TIMEOUT", DEFAULT_TIMEOUT))
        logger.info(f"Распознавание: режим remote, сервис {url}, таймаут {timeout} с")
        return RemoteGateway(url, timeout)

    raise ValueError(f"Неизвестный RECOGNITION_MODE={mode!r}. Допустимо: legacy, remote")
