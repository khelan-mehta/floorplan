# syntax=docker/dockerfile:1
FROM python:3.12-slim AS base
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 SERVICE_NAME=codes
WORKDIR /app

COPY pyproject.toml ./
# Include the [extract] extra so OpenAI-based rule extraction works when OPENAI_API_KEY is set.
RUN pip install --no-cache-dir ".[extract]"

COPY app ./app

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
