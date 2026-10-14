from dataclasses import dataclass, field
from typing import List, Optional, Protocol

STATUS_OK = "ok"
STATUS_NOT_PLANT = "not_plant"


@dataclass(frozen=True)
class RawPrediction:
    """Один ответ нейросети: метка класса и уверенность от 0 до 1"""
    label: str
    confidence: float


@dataclass(frozen=True)
class RecognitionResult:
    """Результат распознавания одной фотографии"""
    status: str  # STATUS_OK или STATUS_NOT_PLANT
    predictions: List[RawPrediction] = field(default_factory=list)
    model_version: Optional[str] = None


class RecognitionUnavailable(Exception):
    """Сервис распознавания недоступен (не отвечает, нет соединения, таймаут)"""


class RecognitionFailed(Exception):
    """Сервис ответил ошибкой. status_code и detail пробрасываются клиенту"""

    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"{status_code}: {detail}")


class RecognitionGateway(Protocol):
    """Интерфейс переключателя"""

    async def recognize_plant(
        self, image: bytes, filename: Optional[str], content_type: Optional[str]
    ) -> RecognitionResult:
        """Определить сорт растения по фото"""
        ...

    async def recognize_disease(
        self, image: bytes, filename: Optional[str], content_type: Optional[str]
    ) -> RecognitionResult:
        """Определить заболевание по фото"""
        ...

    async def aclose(self) -> None:
        """Освободить ресурсы (соединения)"""
        ...
