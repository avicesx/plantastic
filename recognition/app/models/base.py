import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List

import torch
import torch.nn as nn
from PIL import Image

from ..schemas import Prediction

logger = logging.getLogger(__name__)

NORMALIZE_MEAN = [0.485, 0.456, 0.406]
NORMALIZE_STD = [0.229, 0.224, 0.225]


def read_class_names(path: Path) -> List[str]:
    """Читает метки классов, по одной на строку (порядок строк = номера выходов модели)"""
    if not path.is_file():
        raise FileNotFoundError(f"Файл с метками классов не найден: {path}")
    names = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not names:
        raise ValueError(f"Файл с метками классов пуст: {path}")
    return names


class ClassifierModel(ABC):
    """Модель-классификатор: изображение -> вероятности по классам"""

    name: str  # короткое имя: detector / variety / disease

    def __init__(self, weights_path: Path, class_names_path: Path, device: str = "cpu"):
        self.device = torch.device(device)
        self.weights_path = weights_path
        self.class_names = read_class_names(class_names_path)
        self.version = f"{self.name}:{weights_path.stem}"

        if not weights_path.is_file():
            raise FileNotFoundError(f"Файл весов не найден: {weights_path}")

        self.model = self._build(len(self.class_names)).to(self.device)
        checkpoint = torch.load(weights_path, map_location=self.device, weights_only=True)
        state_dict = checkpoint.get("state_dict", checkpoint) if isinstance(checkpoint, dict) else checkpoint
        self.model.load_state_dict(state_dict, strict=True)
        self.model.eval()
        logger.info("Модель %s загружена: %d классов, файл %s", self.name, len(self.class_names), weights_path.name)

    @abstractmethod
    def _build(self, num_classes: int) -> nn.Module:
        """Создаёт архитектуру сети с нужным числом выходов"""

    @abstractmethod
    def preprocess(self, image: Image.Image) -> torch.Tensor:
        """Подготавливает изображение: тензор формы (C, H, W)"""

    @torch.inference_mode()
    def probabilities(self, image: Image.Image) -> torch.Tensor:
        """Вероятности по всем классам (вектор длины num_classes)"""
        batch = self.preprocess(image).unsqueeze(0).to(self.device)
        return torch.softmax(self.model(batch), dim=1)[0]

    def predict(self, image: Image.Image, top_k: int) -> List[Prediction]:
        probs = self.probabilities(image)
        top_probs, top_indices = torch.topk(probs, min(top_k, len(self.class_names)))
        return [
            # softmax в float32 может дать 1.0000001, поэтому ограничиваем диапазоном [0, 1]
            Prediction(label=self.class_names[index], confidence=min(1.0, max(0.0, prob)))
            for prob, index in zip(top_probs.tolist(), top_indices.tolist())
        ]
