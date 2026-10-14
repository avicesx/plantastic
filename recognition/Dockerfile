FROM python:3.13-slim-bookworm

RUN groupadd -r mluser && useradd -r -g mluser mluser

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir torch==2.7.0 --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir torchvision==0.22.0 --no-deps --index-url https://download.pytorch.org/whl/cpu

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=mluser:mluser app ./app

RUN mkdir -p /app/weights && chown mluser:mluser /app /app/weights
USER mluser

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    WEIGHTS_DIR=/app/weights

EXPOSE 8003

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8003"]
