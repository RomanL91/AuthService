"""
Схемы Pydantic (v2) для модели Users.

- UserCreate: вход при регистрации (email, password, full_name?)
- UserLogin: вход (email, password)
- UserRead: ответ наружу (без hashed_password)
- UserUpdate: частичное обновление профиля
- PasswordChange: смена пароля (текущий + новый)
- AdminUpdate: админские флаги (is_active/is_superuser)

Все схемы настроены на работу с ORM (from_attributes=True).
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, ConfigDict, SecretStr


# ==== Base ====


class _UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = Field(default=None, max_length=255)

    model_config = ConfigDict(from_attributes=True)


# ==== Create / Login ====


class UserCreate(BaseModel):
    email: EmailStr
    password: SecretStr = Field(min_length=8, max_length=128)
    full_name: Optional[str] = Field(default=None, max_length=255)

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "email": "user@example.com",
                    "password": "Str0ngP@ssw0rd",
                    "full_name": "Jane Doe",
                }
            ]
        },
    )


class UserLogin(BaseModel):
    email: EmailStr
    password: SecretStr = Field(min_length=8, max_length=128)


# ==== Read (ответ наружу) ====


class UserRead(_UserBase):
    id: int
    is_active: bool
    is_superuser: bool
    created_at: datetime
    updated_at: datetime

    # Pydantic сам сконвертит aware datetime в ISO8601


# ==== Partial update профиля ====


class UserUpdate(BaseModel):
    # обновляем только профильные поля (без прав/статусов)
    full_name: Optional[str] = Field(default=None, max_length=255)

    model_config = ConfigDict(from_attributes=True)


# ==== Смена пароля ====


class PasswordChange(BaseModel):
    current_password: SecretStr = Field(min_length=8, max_length=128)
    new_password: SecretStr = Field(min_length=8, max_length=128)


# ==== Админские апдейты ====


class AdminUpdate(BaseModel):
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None
