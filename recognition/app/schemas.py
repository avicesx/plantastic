from typing import List, Literal
from pydantic import BaseModel, Field


class Prediction(BaseModel):
    label: str = Field(..., description="Метка класса (строка из class_names.txt)")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Уверенность модели, от 0 до 1")


class RecognitionResponse(BaseModel):
    status: Literal["ok", "not_plant"] = Field(
        ..., description="ok - есть предсказания, not_plant - на фото не обнаружено растение"
    )
    model_version: str = Field(..., description="Модель, давшая ответ, например variety:model_epoch_27")
    predictions: List[Prediction] = Field(default_factory=list)


class LabelsResponse(BaseModel):
    kind: Literal["plant", "disease"]
    model_version: str
    labels: List[str]


class ModelState(BaseModel):
    loaded: bool
    version: str | None = None
    classes: int | None = None
    error: str | None = None


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    models: dict[str, ModelState]
