import logging
from typing import List, Literal, Optional
import httpx
from pydantic import BaseModel, ValidationError

from .base import (
    RawPrediction,
    RecognitionFailed,
    RecognitionResult,
    RecognitionUnavailable,
)

logger = logging.getLogger(__name__)


class _Prediction(BaseModel):
    label: str
    confidence: float


class _Response(BaseModel):
    status: Literal["ok", "not_plant"]
    model_version: str
    predictions: List[_Prediction]


class RemoteGateway:
    def __init__(self, base_url: str, timeout: float = 10.0):
        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            timeout=httpx.Timeout(timeout, connect=3.0),
        )

    async def recognize_plant(
        self, image: bytes, filename: Optional[str], content_type: Optional[str]
    ) -> RecognitionResult:
        return await self._call("/v1/plant", image, filename, content_type)

    async def recognize_disease(
        self, image: bytes, filename: Optional[str], content_type: Optional[str]
    ) -> RecognitionResult:
        return await self._call("/v1/disease", image, filename, content_type)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def _call(
        self, path: str, image: bytes, filename: Optional[str], content_type: Optional[str]
    ) -> RecognitionResult:
        files = {"file": (filename or "image", image, content_type or "application/octet-stream")}
        try:
            response = await self._client.post(path, files=files)
        except (httpx.ConnectError, httpx.TimeoutException) as error:
            raise RecognitionUnavailable(f"Сервис recognition не отвечает: {error!r}") from error
        except httpx.HTTPError as error:
            raise RecognitionFailed(500, f"Ошибка при обращении к сервису recognition: {error!r}") from error

        if response.status_code >= 400:
            raise RecognitionFailed(response.status_code, _extract_detail(response))

        try:
            data = _Response.model_validate(response.json())
        except (ValueError, ValidationError) as error:
            raise RecognitionFailed(502, f"Неожиданный ответ сервиса recognition: {error}") from error

        return RecognitionResult(
            status=data.status,
            predictions=[RawPrediction(p.label, p.confidence) for p in data.predictions],
            model_version=data.model_version,
        )


def _extract_detail(response: httpx.Response) -> str:
    try:
        detail = response.json().get("detail")
        if detail:
            return str(detail)
    except (ValueError, AttributeError):
        pass
    return response.text[:200] or f"HTTP {response.status_code}"
