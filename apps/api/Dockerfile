# syntax=docker/dockerfile:1
# Build from the repo root so the canonical JSON Schemas can be bundled for domain validation:
#   docker build -f apps/api/Dockerfile .
FROM python:3.12-slim AS base
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 SERVICE_NAME=api SCHEMAS_DIR=/app/schemas
WORKDIR /app

COPY apps/api/pyproject.toml ./
RUN pip install --no-cache-dir .

ENV FPG_EXAMPLES_DIR=/app/examples
COPY apps/api/app ./app
COPY apps/api/alembic.ini ./alembic.ini
COPY infra/migrations ./infra/migrations
COPY packages/schemas/schemas ./schemas
COPY packages/schemas/examples ./examples

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
