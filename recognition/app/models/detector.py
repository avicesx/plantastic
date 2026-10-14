import torch
import torch.nn as nn
import torchvision.transforms as transforms
from PIL import Image
from torchvision import models

from .base import NORMALIZE_MEAN, NORMALIZE_STD, ClassifierModel

PLANT_LABEL = "plant"
PLANT_THRESHOLD = 0.5


class PlantDetector(ClassifierModel):
    name = "detector"

    _transform = transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
        transforms.Normalize(mean=NORMALIZE_MEAN, std=NORMALIZE_STD),
    ])

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if PLANT_LABEL not in self.class_names:
            raise ValueError(f"В метках детектора нет класса {PLANT_LABEL!r}: {self.class_names}")
        self._plant_index = self.class_names.index(PLANT_LABEL)

    def _build(self, num_classes: int) -> nn.Module:
        model = models.mobilenet_v3_small(weights=None)
        model.classifier[3] = nn.Linear(model.classifier[3].in_features, num_classes)
        return model

    def preprocess(self, image: Image.Image) -> torch.Tensor:
        return self._transform(image)

    def is_plant(self, image: Image.Image) -> bool:
        return float(self.probabilities(image)[self._plant_index]) > PLANT_THRESHOLD
