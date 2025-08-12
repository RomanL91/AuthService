# AuthService — сервис авторизации на FastAPI (JWT с ротацией refresh)

[![Python](https://img.shields.io/badge/Python-3.12-3776AB)](#)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.11x-009688)](#)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-336791)](#)
[![Docker](https://img.shields.io/badge/Docker-ready-0db7ed)](#)

Мини‑сервис авторизации:

* **FastAPI** + **SQLAlchemy (async)** + **Alembic**
* JWT **RS256**: `access` / `refresh`, «семьи» ротаций, защита от reuse
* UoW + репозитории, централизованный маппинг ошибок, подробная OpenAPI

---

## Содержание

* [Структура проекта](#структура-проекта)
* [Требования](#требования)
* [Конфигурация (ENV)](#конфигурация-env)
* [Генерация RSA‑ключей](#генерация-rsa-ключей)
* [Запуск в Docker](#запуск-в-docker)
* [Миграции Alembic](#миграции-alembic)
* [Эндпоинты](#эндпоинты)
* [Примеры cURL](#примеры-curl)
* [Модели и поведение](#модели-и-поведение)
* [Безопасность паролей](#безопасность-паролей)
* [Лицензия](#лицензия)

---

## Структура проекта

```
./
├─ Dockerfile                   # multi-stage образ (poetry + runtime)
├─ docker-compose.yml           # сервис приложения (БД — отдельно)
├─ entrypoint.sh                # старт контейнера: ожидание БД + миграции + запуск сервера
├─ alembic.ini                  # конфиг Alembic
├─ certs/                       # RSA-ключи (если кладём рядом с корнем)
├─ DATABASE/                    # (опционально) compose БД и .env для БД
└─ src/
   ├─ main.py                   # создание FastAPI, lifespan, роутеры
   ├─ .env                      # переменные окружения для приложения
   ├─ api/
   │  └─ v1/                    # роуты и docs
   │     ├─ auth/               # login/refresh/logout/... endpoints
   │     ├─ users/              # register/me
   │     ├─ api_depends.py      # DI: UoW, сервисы, JWTBearer
   │     ├─ errors.py           # централизованный маппинг ошибок
   │     └─ ruotings.py         # сборка router v1
   ├─ apps/
   │  ├─ users/                 # модель/схемы/репозиторий/сервис пользователей
   │  └─ auth/                  # модели/репозитории/сервис auth (sessions/tokens)
   ├─ core/
   │  ├─ settings.py            # pydantic-settings, SettingsAuth и др.
   │  ├─ db_manager.py          # DataBaseManager + session_factory
   │  ├─ models_mixins.py       # Base/IntPK/Timestamps/ActiveFlag
   │  └─ security.py            # bcrypt/Passlib (хэширование паролей)
   ├─ infra/
   │  ├─ repository.py          # generic SQLAlchemyRepository
   │  └─ UoW.py                 # UnitOfWork (ленивые репозитории)
   ├─ migrations/               # Alembic env.py + версии
   └─ certs/                    # RSA-ключи (вариант — хранить здесь)
```

> ⚠️ В проекте есть **две** папки `certs/`: в корне и в `src/`. Выберите **одну** (см. раздел «JWT‑ключи»).

---

## Требования

* Python **3.12** (для локального запуска)
* PostgreSQL **15+**
* Poetry **1.8+**
* Docker / Docker Compose
* OpenSSL (для генерации RSA‑ключей)

---

## Конфигурация (ENV)

Файл `src/.env` (пример уже в репо):

| Ключ                  | Описание                  | Пример/дефолт                                        |
| --------------------- | ------------------------- | ---------------------------------------------------- |
| `POSTGRES_DB`         | Имя БД                    | `AuthServiceBD`                                      |
| `POSTGRES_USER`       | Пользователь БД           | `AuthServiceUser`                                    |
| `POSTGRES_PASSWORD`   | Пароль БД                 | `AuthServicePassword`                                |
| `POSTGRES_HOST`       | Хост БД                   | `localhost` (локально) / **имя контейнера** в Docker |
| `POSTGRES_PORT`       | Порт БД                   | `9999` (локально) / `5432` (обычно в Docker-сети)    |
| `ECHO`                | SQLAlchemy echo (0/1)     | `1`                                                  |
| `SERVICE_HOST`        | Адрес приложения          | `localhost` (локально) / `0.0.0.0` (в контейнере)    |
| `SERVICE_PORT`        | Порт приложения           | `9998`                                               |
| `SERVICE_RELOAD`      | Перезапуск при изменениях | `1` локально / `0` в контейнере                      |
| `JWT_ALG`             | Алгоритм JWT              | `RS256`                                              |
| `JWT_TYPE_FIELD`      | Поле с типом токена       | `type`                                               |
| `JWT_TOKEN_TYPE`      | Тип для клиентов          | `Bearer`                                             |
| `JWT_ACCESS_TYPE`     | Имя access-типа           | `access`                                             |
| `JWT_REFRESH_TYPE`    | Имя refresh-типа          | `refresh`                                            |
| `JWT_ACCESS_TTL_MIN`  | TTL access (мин)          | `15`                                                 |
| `JWT_REFRESH_TTL_MIN` | TTL refresh (мин)         | `20160` (14 дней)                                    |

> 💡 **Docker:** если БД в отдельном контейнере, внутри приложения `POSTGRES_HOST` должен быть равен **имени сервиса БД** (например, `auth_service_database`) или `host.docker.internal`, если БД на хосте.

---

## Генерация RSA‑ключей

```bash
# приватный ключ
openssl genrsa -out private.pem 4096
# публичный ключ
openssl rsa -in private.pem -pubout -out public.pem
```

Положите `private.pem` и `public.pem` в выбранную папку `certs/`.

* **Копировать в образ** (рекомендуется): `src/certs/` → `COPY src/certs/ /app/certs/`
* **Монтировать томом**: `./certs:/app/certs:ro`

Пути по умолчанию задаются в `SettingsAuth` (`core/settings.py`).

---

## Запуск в Docker

### БД уже крутится в отдельном compose

1. Убедитесь, что сеть существует:

```bash
docker network create authnetwork  # если ещё нет
```

2. В `docker-compose.yml`:

```yaml
services:
  auth_service_main:
    build:
      context: .
      dockerfile: Dockerfile
      target: runtime
    container_name: auth_service_main
    env_file:
      - src/.env
    environment:
      SERVICE_HOST: 0.0.0.0
      POSTGRES_HOST: auth_service_database  # имя сервиса БД в сети
      POSTGRES_PORT: 5432                   # порт сервиса БД в сети
      SERVICE_RELOAD: 0
    ports:
      - "9998:9998"
    networks:
      - authnetwork
    restart: unless-stopped
networks:
  authnetwork:
    external: true
```

3. Запуск:

```bash
docker compose up --build
```

Контейнер подождёт БД, применит миграции и запустит Uvicorn.

UI: `http://localhost:9998/docs`, ReDoc: `http://localhost:9998/redoc`.

## Эндпоинты

Базовый префикс: **`/auth_api/v1`**

| Метод  | Путь               | Auth              | Описание                   |
| ------ | ------------------ | ----------------- | -------------------------- |
| `POST` | `/users/register`  | —                 | Регистрация пользователя   |
| `GET`  | `/users/me`        | `Bearer <access>` | Текущий профиль            |
| `POST` | `/auth/login`      | —                 | Вход, выдаёт пару токенов  |
| `POST` | `/auth/refresh`    | `Bearer <refresh>`| Ротация, выдаёт новую пару |
| `POST` | `/auth/logout`     | `Bearer <refresh>`| Выход из текущей сессии    |
| `POST` | `/auth/logout-all` | `Bearer <access>` | Выход со всех устройств    |
| `GET`  | `/auth/sessions`   | `Bearer <access>` | Список активных сессий     |

> 🔒 Замочек в Swagger означает, что точка защищена `JWTBearer` (access/refresh).

---

## Примеры cURL

```bash
# Регистрация
curl -X POST http://localhost:9998/auth_api/v1/users/register \
  -H 'Content-Type: application/json' \
  -d '{"email":"user@example.com","password":"Str0ng!Passw0rd","full_name":"Alice"}'

# Логин → пара токенов
curl -X POST http://localhost:9998/auth_api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -H 'User-Agent: DemoClient/1.0' \
  -d '{"email":"user@example.com","password":"Str0ng!Passw0rd"}'

# Профиль (access)
curl http://localhost:9998/auth_api/v1/users/me \
  -H 'Authorization: Bearer <ACCESS>'

# Ротация (refresh)
curl -X 'POST' \
  'http://localhost:9998/auth_api/v1/auth/refresh' \
  -H 'accept: application/json' \
  -H 'Authorization: Bearer <REFRESH>' \
  -d ''
```

---

## Модели и поведение

* **Users** — пользователи; пароли хранятся **в виде хэша** (bcrypt/Passlib).
* **AuthSessions** — «устройство/браузер»: `session_id`, `user_agent`, `ip_address`, `last_seen_at`, `revoked_at/reason`.
* **RefreshTokens** — история refresh: хранится **хэш** токена (`sha256`), есть `family_id` и `jti`.
  При предъявлении старого/отозванного refresh — ревокация всей семьи и сессии (reuse‑защита).

---

## Безопасность паролей

* Используется **bcrypt** через Passlib (`core/security.py`).
* Хранить только хэш. Никогда не логируем raw‑пароли.
* Сложность и правила — на стороне валидации схем / клиента.

---


## Лицензия

См. файл `LICENSE` в корне.
