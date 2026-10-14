import logging
from datetime import datetime
from typing import List, Optional
import httpx
from pydantic import BaseModel, ValidationError
from starlette.concurrency import run_in_threadpool

from plant_detector.plant_detector import PlantDetector

from .base import (
    STATUS_NOT_PLANT,
    STATUS_OK,
    RawPrediction,
    RecognitionFailed,
    RecognitionResult,
    RecognitionUnavailable,
)

logger = logging.getLogger(__name__)

CLASSIFIER_URL = "http://classifier:8001/classifier/classify"
DISEASE_URL = "http://disease:8002/disease/predict"
LEGACY_MODEL_VERSION = "legacy"


class _OldPrediction(BaseModel):
    class_name: str
    confidence: float


class _OldContent(BaseModel):
    predictions: List[_OldPrediction]
    filename: str
    processed_at: datetime


class _OldResponse(BaseModel):
    success: bool
    data: _OldContent


class LegacyGateway:
    def __init__(self, timeout: float = 7.0):
        self._detector = PlantDetector()
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(timeout, connect=3.0))

    async def recognize_plant(
        self, image: bytes, filename: Optional[str], content_type: Optional[str]
    ) -> RecognitionResult:
        return await self._call(CLASSIFIER_URL, "classifier", image, filename, content_type)

    async def recognize_disease(
        self, image: bytes, filename: Optional[str], content_type: Optional[str]
    ) -> RecognitionResult:
        return await self._call(DISEASE_URL, "disease", image, filename, content_type)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def _call(
        self, url: str, name: str, image: bytes, filename: Optional[str], content_type: Optional[str]
    ) -> RecognitionResult:
        if not await run_in_threadpool(self._detector.predict, image):
            logger.info("На поступившем изображении не обнаружено растение")
            return RecognitionResult(STATUS_NOT_PLANT, [], LEGACY_MODEL_VERSION)

        files = {"file": (filename, image, content_type)}
        try:
            response = await self._client.post(url, files=files)
        except (httpx.ConnectError, httpx.TimeoutException) as error:
            raise RecognitionUnavailable(f"Контейнер {name} не отвечает: {error!r}") from error
        except httpx.HTTPError as error:
            raise RecognitionFailed(500, f"Ошибка при обращении к контейнеру {name}: {error!r}") from error

        if response.status_code >= 400:
            raise RecognitionFailed(response.status_code, response.text[:200])

        try:
            data = _OldResponse.model_validate(response.json())
        except (ValueError, ValidationError) as error:
            raise RecognitionFailed(502, f"Неожиданный ответ контейнера {name}: {error}") from error

        return RecognitionResult(
            status=STATUS_OK,
            predictions=[RawPrediction(p.class_name, p.confidence) for p in data.data.predictions],
            model_version=LEGACY_MODEL_VERSION,
        )
