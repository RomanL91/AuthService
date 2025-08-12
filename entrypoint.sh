#!/usr/bin/env bash
set -e

# Ждём БД (простенько). Можно заменить на wait-for-it.sh
if [ -n "$POSTGRES_HOST" ] && [ -n "$POSTGRES_PORT" ]; then
  echo "Waiting for Postgres at ${POSTGRES_HOST}:${POSTGRES_PORT}..."
  for i in {1..15}; do
    nc -z "${POSTGRES_HOST}" "${POSTGRES_PORT}" && break
    echo "--> ${i}"
    sleep 1
  done
fi

# Применяем миграции Alembic
echo "Running migrations..."
alembic upgrade head

# Стартуем API
echo "Starting uvicorn..."
exec uvicorn main:app --host 0.0.0.0 --port ${SERVICE_PORT:-9998} --app-dir /app/src
