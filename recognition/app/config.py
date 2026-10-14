import os
from dataclasses import dataclass
from pathlib import Path

# Папка с весами. В контейнере монтируется как том в /app/weights
WEIGHTS_DIR = Path(os.getenv("WEIGHTS_DIR", Path(__file__).resolve().parent.parent / "weights"))

# Ограничения на входное изображение
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 МБ
ALLOWED_IMAGE_FORMATS = {"JPEG", "PNG", "WEBP", "HEIF"}  # названия форматов в Pillow

# Сколько предсказаний возвращать
TOP_K = 3

# Сколько изображений обрабатывается нейросетью одновременно
# (остальные запросы ждут в очереди, чтобы не перегружать процессор)
INFERENCE_CONCURRENCY = int(os.getenv("INFERENCE_CONCURRENCY", "2"))

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")


@dataclass(frozen=True)
class ModelFiles:
    weights: Path
    class_names: Path


DETECTOR_FILES = ModelFiles(
    weights=WEIGHTS_DIR / "detector" / "model_epoch_10.pth",
    class_names=WEIGHTS_DIR / "detector" / "class_names.txt",
)
VARIETY_FILES = ModelFiles(
    weights=WEIGHTS_DIR / "variety" / "model_epoch_27.pth",
    class_names=WEIGHTS_DIR / "variety" / "class_names.txt",
)
DISEASE_FILES = ModelFiles(
    weights=WEIGHTS_DIR / "disease" / "trained_convnext_best.pth",
    class_names=WEIGHTS_DIR / "disease" / "class_names.txt",
)