FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN apt-get update && apt-get install -y --no-install-recommends libatomic1 && rm -rf /var/lib/apt/lists/*
RUN python -m playwright install --with-deps chromium
COPY alembic.ini .
COPY alembic ./alembic
COPY app ./app
COPY models ./models
EXPOSE 8000
CMD ["sh", "-c", "python -m app.docker_bootstrap --ensure-alembic && alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8000"]
