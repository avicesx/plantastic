import torch
import torch.nn as nn
import torchvision.transforms as transforms
from PIL import Image
from torchvision import models

from .base import NORMALIZE_MEAN, NORMALIZE_STD, ClassifierModel


class DiseaseClassifier(ClassifierModel):
    name = "disease"

    _transform = transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
        transforms.Normalize(mean=NORMALIZE_MEAN, std=NORMALIZE_STD),
    ])

    def _build(self, num_classes: int) -> nn.Module:
        model = models.convnext_base(weights=None)
        model.classifier[2] = nn.Sequential(
            nn.Dropout(p=0.7),
            nn.Linear(model.classifier[2].in_features, num_classes),
        )
        return model

    def preprocess(self, image: Image.Image) -> torch.Tensor:
        return self._transform(image)
