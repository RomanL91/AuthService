class RegisterPointDoc:
    summary = "Регистрация (создание) нового пользователя"
    description = (
        "Создаёт новую учётную запись.\n\n"
        "**Правила и поведение:**\n"
        "- `email` должен быть уникальным (регистронезависимо).\n"
        "- Пароль передаётся как `SecretStr`, хранится в базе **в виде хэша**.\n"
        "- Поле `full_name` необязательно.\n"
        "- При успехе возвращаются основные поля профиля (без пароля).\n\n"
        "**Ответы:**\n"
        "- **201** — пользователь создан;\n"
        "- **409** — такой e-mail уже зарегистрирован;\n"
        "- **422** — ошибки валидации входных данных.\n"
    )
    responses = {
        201: {
            "description": "Пользователь успешно создан",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "email": "sidorov@example.com",
                        "full_name": "Ivan Sidorov",
                        "is_active": True,
                        "is_superuser": False,
                        "created_at": "2025-08-12T10:15:30+00:00",
                        "updated_at": "2025-08-12T10:15:30+00:00",
                    }
                }
            },
        },
        409: {
            "description": "E-mail уже зарегистрирован",
            "content": {
                "application/json": {"example": {"detail": "Email already registered"}}
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
                                "full_name": "Ivan Sidorov",
                            },
                        }
                    }
                }
            }
        }
    }


class MePointDoc:
    summary = "Профиль текущего пользователя (чтение)"
    description = (
        "Возвращает профиль пользователя, идентификатор которого берётся из **access-токена**.\n\n"
        "**Требования:**\n"
        "- Заголовок `Authorization: Bearer <access_token>` (тип токена — `access`).\n\n"
        "**Что возвращается:**\n"
        "- Основные поля профиля: `id`, `email`, `full_name`, `is_active`, `is_superuser`, "
        "`created_at`, `updated_at`.\n"
        "- Пароль и любые секретные данные **никогда** не возвращаются.\n\n"
        "**Ответы:**\n"
        "- **200** — профиль найден и возвращён;\n"
        "- **401** — отсутствует/недействительный или просроченный токен;\n"
        "- **403** — пользователь деактивирован (`is_active = false`);\n"
        "- **404** — пользователь не найден.\n"
    )

    responses = {
        200: {
            "description": "OK — профиль текущего пользователя",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "email": "sidorov@example.com",
                        "full_name": "Ivan Sidorov",
                        "is_active": True,
                        "is_superuser": False,
                        "created_at": "2025-08-12T10:15:30+00:00",
                        "updated_at": "2025-08-12T10:15:30+00:00",
                    }
                }
            },
        },
        401: {
            "description": "Unauthorized — отсутствует/недействительный или просроченный access-токен",
            "content": {
                "application/json": {
                    "examples": {
                        "missing": {"value": {"detail": "Not authenticated"}},
                        "expired": {"value": {"detail": "Token expired"}},
                        "invalid": {"value": {"detail": "Invalid token"}},
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
        404: {
            "description": "Not Found — пользователь не найден",
            "content": {"application/json": {"example": {"detail": "User not found"}}},
        },
    }
