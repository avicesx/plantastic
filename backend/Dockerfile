# Используем официальный образ Python как базовый.
# Выбирайте версию, соответствующую вашему проекту.
FROM python:3.13-slim-bookworm AS builder

# Установка системных зависимостей, если они нужны.
# Например, если у вас есть библиотеки, которым нужны компиляторы (например, psycopg2).
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Установка рабочей директории внутри образа
WORKDIR /app

# Копируем только файл requirements.txt, чтобы воспользоваться кешированием Docker.
# Если requirements.txt не изменится, этот шаг не будет пересобираться.
COPY requirements.txt .

# Установка Python-зависимостей.
# --no-cache-dir для уменьшения размера образа.
# -r requirements.txt для установки зависимостей из файла.
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Копируем остальной код приложения.
# .dockerignore поможет исключить ненужные файлы (venv, .git, __pycache__).
COPY . .


# Этап 2: Финальный образ (для уменьшения размера итогового образа)
FROM python:3.13-slim-bookworm

# Создаем непривилегированного пользователя для безопасности
# RUN groupadd -r appuser && useradd -r -g appuser appuser
RUN groupadd -g 1002 developers && \
    groupadd -g 1000 appuser && \
    useradd -r -u 1000 -g appuser -G developers appuser
    
# Установка только необходимых runtime зависимостей
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Установка рабочей директории
WORKDIR /app

# Копируем установленные Python-зависимости из 'builder' этапа.
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Копируем код приложения из 'builder' этапа.
COPY --from=builder /app /app

# Создаем директории для данных и логов
RUN mkdir -p /app/data /app/logs && \
    chown -R appuser:appuser /app

USER appuser

# Открытие порта, на котором будет работать ваш бэкенд.
# Замените 8000 на порт вашего приложения (например, 5000 для Flask, 8000 для Django/FastAPI).
EXPOSE 8000

# Определение переменной окружения для лучшего вывода логов.
ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE=1

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Команда для запуска вашего приложения.
# Используйте Gunicorn или Uvicorn для продакшн-развертывания WSGI/ASGI приложений.
# Замените 'your_project.wsgi:application' или 'main:app' на актуальный путь к вашему приложению.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]