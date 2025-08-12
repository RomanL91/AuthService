# ===== Base =====
FROM python:3.12-slim AS base
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    POETRY_VERSION=1.8.3 \
    POETRY_HOME=/opt/poetry \
    POETRY_VIRTUALENVS_CREATE=false \
    PATH="/opt/poetry/bin:${PATH}"

# Системные зависимости (минимум). Колёсики для bcrypt/cffi обычно есть, так что без gcc.
RUN apt-get update && apt-get install -y --no-install-recommends \
    tzdata curl ca-certificates netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# Установка Poetry в POETRY_HOME и добавление в PATH
RUN curl -sSL https://install.python-poetry.org | python3 - --version $POETRY_VERSION

WORKDIR /app

# Только манифесты — для лучшего кеша
COPY pyproject.toml poetry.lock* /app/

# Устанавливаем зависимости (без dev)
RUN poetry install --only main --no-interaction --no-ansi

# ===== Runtime =====
FROM base AS runtime
WORKDIR /app

# Копируем исходники
COPY src/ /app/src/
# (Если есть) корневой alembic.ini
COPY alembic.ini /app/alembic.ini
# (Если миграции лежат в src/migrations — ничего не надо, мы их уже скопировали)

# Убедимся, что Python видит src как пакет
ENV PYTHONPATH=/app/src

# Сюда положим стартовый скрипт
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Внешний порт сервиса
EXPOSE 9998

# По умолчанию: миграции -> uvicorn
ENTRYPOINT ["/entrypoint.sh"]
