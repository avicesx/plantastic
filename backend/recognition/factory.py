import logging
import os
from .base import RecognitionGateway
from .remote import RemoteGateway

logger = logging.getLogger(__name__)

DEFAULT_RECOGNITION_URL = "http://recognition:8003"
DEFAULT_TIMEOUT = 10.0


def create_gateway() -> RecognitionGateway:
    url = os.getenv("RECOGNITION_URL", DEFAULT_RECOGNITION_URL)
    timeout = float(os.getenv("RECOGNITION_TIMEOUT", DEFAULT_TIMEOUT))
    logger.info(f"Распознавание: сервис {url}, таймаут {timeout} с")
    return RemoteGateway(url, timeout)