import logging
from typing import Dict, Optional, Type
from fastapi import HTTPException, status
from . import config
from .models import ClassifierModel, DiseaseClassifier, PlantDetector, VarietyClassifier
from .schemas import ModelState

logger = logging.getLogger(__name__)

# имя -> (класс модели, файлы)
MODEL_SPECS: Dict[str, tuple[Type[ClassifierModel], config.ModelFiles]] = {
    "detector": (PlantDetector, config.DETECTOR_FILES),
    "variety": (VarietyClassifier, config.VARIETY_FILES),
    "disease": (DiseaseClassifier, config.DISEASE_FILES),
}


class ModelRegistry:
    def __init__(self):
        self.models: Dict[str, ClassifierModel] = {}
        self.errors: Dict[str, str] = {}

    def load_all(self) -> None:
        for name, (model_class, files) in MODEL_SPECS.items():
            try:
                self.models[name] = model_class(files.weights, files.class_names)
            except Exception as error:  # одна сломанная модель не должна ронять весь сервис
                self.errors[name] = f"{type(error).__name__}: {error}"
                logger.exception("Не удалось загрузить модель %s", name)

    def require(self, name: str) -> ClassifierModel:
        """Возвращает загруженную модель или отвечает 503, если она недоступна"""
        model = self.models.get(name)
        if model is None:
            reason = self.errors.get(name, "модель не загружена")
            raise HTTPException(
                status.HTTP_503_SERVICE_UNAVAILABLE,
                f"Модель {name} недоступна: {reason}",
            )
        return model

    def get(self, name: str) -> Optional[ClassifierModel]:
        return self.models.get(name)

    def states(self) -> Dict[str, ModelState]:
        result: Dict[str, ModelState] = {}
        for name in MODEL_SPECS:
            model = self.models.get(name)
            if model is not None:
                result[name] = ModelState(loaded=True, version=model.version, classes=len(model.class_names))
            else:
                result[name] = ModelState(loaded=False, error=self.errors.get(name, "не загружена"))
        return result

    @property
    def all_loaded(self) -> bool:
        return all(name in self.models for name in MODEL_SPECS)
