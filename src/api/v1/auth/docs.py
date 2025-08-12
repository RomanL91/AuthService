class LoginPointDoc:
    summary = "Вход (создание сессии) и выдача пары токенов"
    description = (
        "Аутентифицирует пользователя по `email` и `password`, создаёт **сессию** устройства/браузера "
        "и возвращает пару JWT-токенов: **access** и **refresh**.\n\n"
        "**Поведение и правила:**\n"
        "- Пароль сравнивается с хэшем, хранимым в базе (в ответе пароль никогда не возвращается).\n"
        "- При успехе создаётся запись сессии (фиксируются `user_agent`, `ip_address`, `last_seen_at`).\n"
        "- В `access_token` краткий TTL (используется для авторизации в API), в `refresh_token` — длительный TTL (для обновления пары).\n"
        "- Точка **не требует** авторизации и может вызываться анонимно.\n"
        "- Тип токена в заголовках — `Bearer`.\n\n"
        "**Ответы:**\n"
        "- **200** — возвращена пара токенов и параметры их использования;\n"
        "- **401** — неверные учётные данные (всегда общее сообщение);\n"
        "- **403** — учётная запись деактивирована (`is_active = false`);\n"
        "- **422** — ошибки валидации входных данных.\n"
    )

    responses = {
        200: {
            "description": "ОК — выдана пара токенов",
            "content": {
                "application/json": {
                    "example": {
                        "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
                        "refresh_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
                        "token_type": "Bearer",
                        "expires_in": 900,
                    }
                }
            },
        },
        401: {
            "description": "Unauthorized — неверные учётные данные",
            "headers": {
                "WWW-Authenticate": {
                    "schema": {"type": "string"},
                    "description": "Всегда 'Bearer' для совместимости клиентов",
                }
            },
            "content": {
                "application/json": {
                    "examples": {
                        "invalid": {"value": {"detail": "Invalid credentials"}}
                    }
                }
            },
        },
        403: {
            "description": "Forbidden — пользователь деактивирован",
            "content": {
                "application/json": {"example": {"detail": "User is inactive"}}
            },
        },
        422: {"description": "Ошибки валидации входных данных"},
    }

    openapi_extra = {
        "requestBody": {
            "content": {
                "application/json": {
                    "examples": {
                        "basic": {
                            "summary": "Пример запроса",
                            "value": {
                                "email": "sidorov@example.com",
                                "password": "Str0ng!Passw0rd",
                            },
                        }
                    }
                }
            }
        },
    }


class LogoutPointDoc:
    summary = "Выход из текущей сессии (revoke by refresh)"
    description = (
        "Отзывает **текущую сессию** пользователя по переданному `refresh_token`.\n\n"
        "**Поведение и правила:**\n"
        "- Принимает `refresh_token` в теле запроса (тип токена должен быть `refresh`).\n"
        "- Токен проверяется на подпись и срок действия; при успехе связанную сессию помечает как отозванную.\n"
        "- Операция **идемпотентна**: повторный вызов с тем же токеном также вернёт `204 No Content`.\n"
        "- Точка **не требует** access-токена — достаточно валидного refresh-токена.\n\n"
        "**Ответы:**\n"
        "- **204** — сессия отозвана (или уже была отозвана ранее);\n"
        "- **400** — тип токена неверный (ожидался `refresh`);\n"
        "- **401** — токен просрочен или недействителен;\n"
        "- **422** — ошибки валидации входных данных.\n"
    )

    responses = {
        204: {"description": "Logged out — текущая сессия отозвана"},
        400: {
            "description": "Invalid token type",
            "content": {
                "application/json": {
                    "examples": {
                        "wrong_type": {"value": {"detail": "Invalid token type."}}
                    }
                }
            },
        },
        401: {
            "description": "Invalid/expired token",
            "headers": {
                "WWW-Authenticate": {
                    "schema": {"type": "string"},
                    "description": "Обычно 'Bearer' для совместимости клиентов",
                }
            },
            "content": {
                "application/json": {
                    "examples": {
                        "expired": {"value": {"detail": "Token expired."}},
                        "invalid": {"value": {"detail": "Invalid token"}},
                    }
                }
            },
        },
        422: {"description": "Ошибки валидации входных данных"},
    }

    openapi_extra = {
        "requestBody": {
            "required": True,
            "content": {
                "application/json": {
                    "examples": {
                        "basic": {
                            "summary": "Пример запроса",
                            "value": {
                                "refresh_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."
                            },
                        }
                    }
                }
            },
        },
    }


class RefreshPointDoc:
    summary = "Обновление пары токенов (refresh → новая пара access/refresh)"
    description = (
        "Принимает действительный **refresh-токен** из заголовка "
        "`Authorization: Bearer <refresh_token>`, выполняет ротацию и возвращает **новую пару**: "
        "`access_token` и `refresh_token`.\n\n"
        "**Как работает ротация:**\n"
        "1. Проверяется подпись и срок действия refresh-токена.\n"
        "2. Старый refresh помечается как использованный; создаются **новый refresh** (в той же «семье») и **новый access**.\n"
        "3. Возвращается новая пара токенов; старый refresh повторно использовать нельзя.\n\n"
        "**Защита от повторного использования (reuse):**\n"
        "- Если предъявлен ранее использованный/отозванный refresh, ревокается вся «семья» токенов и текущая сессия, "
        "ответ — **401 Unauthorized**. Клиент должен заново выполнить **login**.\n\n"
        "**Правила и требования:**\n"
        "- Точка **не требует** access-токена — достаточно валидного refresh-токена.\n"
        "- Тип входного токена обязан быть `refresh`.\n"
        "- В ответе: `token_type = Bearer` и `expires_in` (TTL access-токена в секундах).\n"
        "- После ответа **замените** у клиента обе копии токенов на новые.\n"
    )

    responses = {
        200: {
            "description": "ОК — выдана новая пара токенов",
            "content": {
                "application/json": {
                    "example": {
                        "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
                        "refresh_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
                        "token_type": "Bearer",
                        "expires_in": 900,
                    }
                }
            },
        },
        400: {
            "description": "Invalid token type (ожидался refresh) или некорректный формат клеймов",
            "content": {
                "application/json": {
                    "examples": {
                        "wrong_type": {"value": {"detail": "Invalid token type."}},
                        "malformed": {"value": {"detail": "Malformed refresh token."}},
                    }
                }
            },
        },
        401: {
            "description": "Unauthorized — токен просрочен/недействителен или обнаружен повторный показ (reuse)",
            "headers": {
                "WWW-Authenticate": {
                    "schema": {"type": "string"},
                    "description": "Обычно 'Bearer' для совместимости клиентов",
                }
            },
            "content": {
                "application/json": {
                    "examples": {
                        "expired": {"value": {"detail": "Token expired."}},
                        "invalid": {"value": {"detail": "Invalid token"}},
                        "reuse": {"value": {"detail": "Refresh token reuse detected"}},
                        "missing": {"value": {"detail": "Not authenticated"}},
                    }
                }
            },
        },
        500: {
            "description": "Внутренняя ошибка — ротация не выполнена",
            "content": {
                "application/json": {"example": {"detail": "Cannot refresh token"}}
            },
        },
    }


class LogoutAllPointDoc:
    summary = "Глобальный выход: отозвать все сессии и refresh-токены пользователя"
    description = (
        "Отзывает **все активные сессии** пользователя и **все refresh-токены** во всех устройствах.\n\n"
        "**Требования:**\n"
        "- Нужен валидный **access-токен** в заголовке `Authorization: Bearer <access>`.\n\n"
        "**Поведение:**\n"
        "- Все записи сессий помечаются как `revoked` (фиксируется причина), все refresh-токены — отзываются.\n"
        "- Операция **идемпотентна** — повторный вызов с тем же пользователем вернёт `204 No Content`.\n"
        "- Уже выданные access-токены обычно остаются валидны до истечения `exp` (если не используется доп. проверка версии/сессии на каждом запросе).\n"
        "  Рекомендуется использовать короткий TTL у access или версионирование токенов для мгновенной инвалидции.\n\n"
        "**Ответы:**\n"
        "- **204** — все сессии и refresh-токены отозваны;\n"
        "- **401** — отсутствует/недействительный/просроченный access-токен;\n"
        "- **422** — ошибки валидации (не ожидаются, так как тело запроса пустое).\n"
    )

    responses = {
        204: {"description": "OK — пользователь разлогинен на всех устройствах"},
        401: {
            "description": "Unauthorized — нет или недействителен access-токен",
            "headers": {
                "WWW-Authenticate": {
                    "schema": {"type": "string"},
                    "description": "Как правило, 'Bearer' для совместимости клиентов",
                }
            },
            "content": {
                "application/json": {
                    "examples": {
                        "missing": {"value": {"detail": "Not authenticated"}},
                        "expired": {"value": {"detail": "Token expired."}},
                        "invalid": {"value": {"detail": "Invalid token"}},
                    }
                }
            },
        },
        422: {"description": "Ошибки валидации входных данных"},
    }

    openapi_extra = {
        "requestBody": {
            "required": False,
            "content": {
                "application/json": {
                    "examples": {
                        "empty": {
                            "summary": "Тело не требуется",
                            "value": {},
                        }
                    }
                }
            },
        },
    }


class SessionsListPointDoc:
    summary = "Список активных сессий текущего пользователя"
    description = (
        "Возвращает **активные** (не отозванные) сессии пользователя, определяемого по **access-токену**.\n\n"
        "**Требования:**\n"
        "- Заголовок `Authorization: Bearer <access_token>` (тип токена — `access`).\n\n"
        "**Что возвращается:**\n"
        "- Массив объектов сессий с полями:\n"
        "  - `session_id` — UUID устройства/браузера;\n"
        "  - `user_agent` — строка User-Agent (может быть `null`);\n"
        "  - `ip_address` — IPv4/IPv6 адрес (может быть `null`);\n"
        "  - `created_at` — время создания сессии (UTC);\n"
        "  - `last_seen_at` — время последней активности (UTC), может быть `null`.\n\n"
        "**Поведение:**\n"
        "- Сессии, у которых проставлен `revoked_at`, **не** возвращаются.\n"
        "- Результат обычно отсортирован по убыванию `last_seen_at`.\n\n"
        "**Ответы:**\n"
        "- **200** — список активных сессий (может быть пустым массивом);\n"
        "- **401** — отсутствует/недействительный/просроченный access-токен;\n"
        "- **422** — ошибки валидации (не ожидаются, тело запроса отсутствует).\n"
    )

    responses = {
        200: {
            "description": "OK — список активных сессий",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "session_id": "f2c1f6a5-6d4b-4f7c-9b2b-8f3b9d2a1e11",
                            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                            "ip_address": "203.0.113.42",
                            "created_at": "2025-08-12T10:15:30+00:00",
                            "last_seen_at": "2025-08-12T11:47:03+00:00",
                        },
                        {
                            "session_id": "9e7b4d0e-9a3f-4f61-8f77-0c8e2f7d2c55",
                            "user_agent": "Safari/605.1.15 (iPhone; iOS 17.4)",
                            "ip_address": "2001:db8::2",
                            "created_at": "2025-08-10T08:02:11+00:00",
                            "last_seen_at": "2025-08-11T21:19:44+00:00",
                        },
                    ]
                }
            },
        },
        401: {
            "description": "Unauthorized — нет или недействителен access-токен",
            "headers": {
                "WWW-Authenticate": {
                    "schema": {"type": "string"},
                    "description": "Как правило, 'Bearer' для совместимости клиентов",
                }
            },
            "content": {
                "application/json": {
                    "examples": {
                        "missing": {"value": {"detail": "Not authenticated"}},
                        "expired": {"value": {"detail": "Token expired."}},
                        "invalid": {"value": {"detail": "Invalid token"}},
                    }
                }
            },
        },
        422: {"description": "Ошибки валидации входных данных"},
    }
