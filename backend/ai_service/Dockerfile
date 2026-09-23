FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app
COPY common/requirements.txt common/
COPY ai_service/requirements.txt ai_service/
RUN pip install --no-cache-dir -r ai_service/requirements.txt
COPY common ./common
COPY ai_service/app ./app
RUN useradd --create-home --uid 10001 appuser
USER appuser
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
