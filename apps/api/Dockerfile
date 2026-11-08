FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml ./
# Bağımlılık katmanı uygulama kodundan ayrılır; kod değişince pip yeniden inmez.
RUN mkdir app && printf "" > app/__init__.py \
  && pip install --no-cache-dir . \
  && rm -rf app

COPY app ./app

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
