# Контекст сборки — корень backend (нужен доступ к common/):
#   docker build -f example_service/Dockerfile .
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

# Сначала зависимости — слой кэшируется, пока requirements не менялись
COPY common/requirements.txt common/requirements-db.txt common/
COPY example_service/requirements.txt example_service/
RUN pip install --no-cache-dir -r example_service/requirements.txt

COPY common ./common
COPY example_service/app ./app

RUN useradd --create-home --uid 10001 appuser
USER appuser

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
