FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Dependencies first: this layer is cached until requirements.txt changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY alembic ./alembic
COPY alembic.ini .

# Non-root user; /data is where the SQLite file lives (mounted as a volume).
RUN useradd --system --no-create-home appuser \
    && mkdir /data \
    && chown appuser /data
USER appuser

ENV DATABASE_URL=sqlite:////data/health_checks.db

EXPOSE 8000

# Apply migrations, then serve. --host 0.0.0.0 makes the port reachable from outside the
# container. A single process: SQLite does not suit multiple writers.
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8000"]
