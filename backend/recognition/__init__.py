"""Модуль «Распознавание» на стороне backend.

Снаружи нужно только то, что перечислено в __all__: интерфейс RecognitionGateway,
типы результата, ошибки и create_gateway(), которая создаёт нужную реализацию.
"""
from .base import (
    STATUS_NOT_PLANT,
    STATUS_OK,
    RawPrediction,
    RecognitionFailed,
    RecognitionGateway,
    RecognitionResult,
    RecognitionUnavailable,
)
from .factory import create_gateway

__all__ = [
    "STATUS_NOT_PLANT",
    "STATUS_OK",
    "RawPrediction",
    "RecognitionFailed",
    "RecognitionGateway",
    "RecognitionResult",
    "RecognitionUnavailable",
    "create_gateway",
]