"""
Базовые классы (миксины) для моделей SQLAlchemy.

Содержимое:
- Base — абстрактный DeclarativeBase с автогенерацией __tablename__ по имени класса.
- IntPKMixin — первичный ключ типа BIGINT с автоинкрементом.
- TimestampMixin — автоматические поля created_at и updated_at (UTC-aware timestamptz).
- ActiveFlagMixin — булево поле is_active с дефолтным значением True.
"""

from __future__ import annotations

from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, declared_attr


class Base(DeclarativeBase):
    __abstract__ = True

    @declared_attr
    def __tablename__(cls) -> str:
        return f"{cls.__name__.lower()}"


class IntPKMixin:
    id: Mapped[int] = mapped_column(
        sa.BigInteger,
        primary_key=True,
        autoincrement=True,
    )


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
        onupdate=sa.func.now(),
    )


class ActiveFlagMixin:
    is_active: Mapped[bool] = mapped_column(
        sa.Boolean,
        nullable=False,
        server_default=sa.text("true"),
    )
