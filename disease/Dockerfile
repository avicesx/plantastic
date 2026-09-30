# Используем официальный образ Python как базовый.
# Выбирайте версию, соответствующую вашему проекту.
FROM python:3.13-slim-bookworm AS builder

# Устанавливаем системные зависимости
#webp изменен на libwebp-dev

#НОВОЕ ниже
RUN apt-get update && apt-get install -y \
    build-essential \
    libjpeg-dev \
    libpng-dev \
    zlib1g-dev \
    libfreetype6-dev \
    liblcms2-dev \
    libwebp-dev \
    libheif-dev \
    libde265-dev \
    libx265-dev \
    # Добавьте другие нужные пакеты \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем файлы зависимостей
COPY requirements2.txt .

# Устанавливаем зависимости Python
#ИЗМЕНЕНО - добавлено установка torch torchvision torchaudio CPU-only
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r requirements2.txt

# Копируем исходный код
COPY . .

# Этап 2: Финальный образ
FROM python:3.13-slim-bookworm

# Создаем непривилегированного пользователя для безопасности
RUN groupadd -r mluser && useradd -r -g mluser mluser
# Устанавливаем только runtime-зависимости
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libjpeg62-turbo \
    libpng16-16 \
    libfreetype6 \
    liblcms2-2 \
    libwebp7 \
    libheif1 \
    libde265-0 \
    libx265-199 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Копируем установленные Python-зависимости
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Копируем код приложения из builder-этапа
COPY --from=builder /app /app

# Создаем директории и устанавливаem права доступа
RUN mkdir -p /app/logs /app/cache && \
    chown -R mluser:mluser /app
# Переключаемся на непривилегированного пользователя
USER mluser

# Открываем порт
# ИЗМЕНЕНО!
EXPOSE 8002

ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE=1 
ENV PYTHONPATH=/app

# # Оптимизация для NumPy/ML библиотек ????????
# ENV OPENBLAS_NUM_THREADS=1
# ENV MKL_NUM_THREADS=1

# ИЗМЕНЕНО!
HEALTHCHECK --interval=30s --timeout=15s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8002/health || exit 1

# Запускаем приложение
# ИЗМЕНЕНО!
CMD ["uvicorn", "disease_app.api.predict:router", "--host", "0.0.0.0", "--port", "8002"] 