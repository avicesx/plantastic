from io import BytesIO
from fastapi import HTTPException, UploadFile, status
from PIL import Image, UnidentifiedImageError
from pillow_heif import register_heif_opener
from .config import ALLOWED_IMAGE_FORMATS, MAX_FILE_SIZE

register_heif_opener()  # поддержка HEIC/HEIF


async def read_image(file: UploadFile) -> Image.Image:
    """Читает загруженный файл и возвращает RGB-изображение
    Ошибки:
    400 - файл пустой
    413 - слишком большой
    415 - не изображение / неподдерживаемый формат
    """
    try:
        data = await file.read(MAX_FILE_SIZE + 1)
    finally:
        await file.close()

    if not data:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Файл пуст")
    if len(data) > MAX_FILE_SIZE:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            f"Размер файла превышает {MAX_FILE_SIZE // (1024 * 1024)} МБ",
        )

    try:
        image = Image.open(BytesIO(data))
        image_format = image.format
        if image_format not in ALLOWED_IMAGE_FORMATS:
            raise HTTPException(
                status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                f"Неподдерживаемый формат {image_format}. Допустимо: JPEG, PNG, WebP, HEIC/HEIF",
            )
        return image.convert("RGB")
    except HTTPException:
        raise
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError) as error:
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            f"Не удалось прочитать изображение: {error}",
        ) from error
