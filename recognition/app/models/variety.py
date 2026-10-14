import torch
import torch.nn as nn
import torchvision.transforms as transforms
from PIL import Image
from torchvision import models

from .base import NORMALIZE_MEAN, NORMALIZE_STD, ClassifierModel

MODEL_INPUT_SIZE = 260   # размер входа EfficientNet-B2
MAX_IMAGE_SIZE = 2048    # слишком большие фото сначала уменьшаются


class VarietyClassifier(ClassifierModel):
    name = "variety"

    _shrink = transforms.Compose([
        transforms.Resize(MAX_IMAGE_SIZE),
        transforms.CenterCrop(MAX_IMAGE_SIZE),
    ])
    _transform = transforms.Compose([
        transforms.Resize((MODEL_INPUT_SIZE, MODEL_INPUT_SIZE)),
        transforms.ToTensor(),
        transforms.Normalize(mean=NORMALIZE_MEAN, std=NORMALIZE_STD),
    ])

    def _build(self, num_classes: int) -> nn.Module:
        model = models.efficientnet_b2(weights=None)
        model.classifier = nn.Sequential(
            nn.Dropout(p=0.2),
            nn.Linear(model.classifier[1].in_features, num_classes),
        )
        return model

    def preprocess(self, image: Image.Image) -> torch.Tensor:
        if max(image.size) > MAX_IMAGE_SIZE:
            image = self._shrink(image)
        return self._transform(image)
