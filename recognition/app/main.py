import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, File, HTTPException, Response, UploadFile, status
from fastapi.concurrency import run_in_threadpool
from PIL import Image

from . import config
from .images import read_image
from .models import ClassifierModel, PlantDetector
from .registry import ModelRegistry
from .schemas import HealthResponse, LabelsResponse, Prediction, RecognitionResponse

logging.basicConfig(
    level=config.LOG_LEVEL,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("recognition")

registry = ModelRegistry()
# Ограничивает число одновременных расчётов нейросетью (создаётся при старте)
_inference_slots: asyncio.Semaphore


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _inference_slots
    _inference_slots = asyncio.Semaphore(config.INFERENCE_CONCURRENCY)
    registry.load_all()
    if registry.all_loaded:
        logger.info("Все модели загружены, сервис готов к работе")
    else:
        logger.error("Сервис запущен не полностью, ошибки загрузки: %s", registry.errors)
    yield


app = FastAPI(
    title="Plantastic Recognition",
    description="Распознавание сорта растения и заболевания по фотографии",
    version="1.0.0",
    lifespan=lifespan,
)


async def _infer(function, *args):
    """Запускает тяжёлый расчёт в отдельном потоке и не даёт запустить слишком много сразу"""
    async with _inference_slots:
        try:
            return await run_in_threadpool(function, *args)
        except Exception as error:
            logger.exception("Ошибка при работе нейросети")
            raise HTTPException(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                f"Ошибка при распознавании: {type(error).__name__}",
            ) from error


async def _recognize(file: UploadFile, classifier_name: str) -> RecognitionResponse:
    # Проверяем доступность моделей до чтения файла: если сервис не готов, отвечаем сразу
    detector: PlantDetector = registry.require("detector")  # type: ignore[assignment]
    classifier: ClassifierModel = registry.require(classifier_name)
    image: Image.Image = await read_image(file)

    if not await _infer(detector.is_plant, image):
        logger.info("На изображении не обнаружено растение")
        return RecognitionResponse(status="not_plant", model_version=detector.version, predictions=[])

    predictions: list[Prediction] = await _infer(classifier.predict, image, config.TOP_K)
    return RecognitionResponse(status="ok", model_version=classifier.version, predictions=predictions)


@app.post("/v1/plant", response_model=RecognitionResponse, summary="Определить сорт растения по фото")
async def recognize_plant(file: UploadFile = File(...)) -> RecognitionResponse:
    return await _recognize(file, "variety")


@app.post("/v1/disease", response_model=RecognitionResponse, summary="Определить заболевание по фото")
async def recognize_disease(file: UploadFile = File(...)) -> RecognitionResponse:
    return await _recognize(file, "disease")


@app.get("/v1/labels/{kind}", response_model=LabelsResponse, summary="Метки классов модели")
async def labels(kind: Literal["plant", "disease"]) -> LabelsResponse:
    model = registry.require("variety" if kind == "plant" else "disease")
    return LabelsResponse(kind=kind, model_version=model.version, labels=model.class_names)


@app.get("/health", response_model=HealthResponse, summary="Состояние сервиса")
async def health(response: Response) -> HealthResponse:
    """200 - все три модели загружены, 503 - хотя бы одна недоступна (сервис при этом продолжает отвечать)"""
    if not registry.all_loaded:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return HealthResponse(
        status="ok" if registry.all_loaded else "degraded",
        models=registry.states(),
    )
