import uuid
from enum import StrEnum
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, INET
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.models_mixins import Base, IntPKMixin, TimestampMixin

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apps.users.models import Users


class RevokeReason(StrEnum):
    USER_LOGOUT = "user_logout"
    REUSE_DETECTED = "reuse_detected"
    ADMIN_FORCE = "admin_force"
    PASSWORD_CHANGE = "password_change"
    ROTATED = "rotated"


class AuthSessions(IntPKMixin, TimestampMixin, Base):

    user_id: Mapped[int] = mapped_column(
        sa.BigInteger,
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # одно физическое устройство/браузер
    session_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        unique=True,
    )

    user_agent: Mapped[str | None] = mapped_column(
        sa.String(255),
    )
    ip_address: Mapped[str | None] = mapped_column(
        INET,
    )

    last_seen_at: Mapped["datetime | None"] = mapped_column(
        sa.DateTime(timezone=True),
    )
    revoked_at: Mapped["datetime | None"] = mapped_column(
        sa.DateTime(timezone=True),
    )
    revoked_reason: Mapped[RevokeReason | None] = mapped_column(
        sa.Enum(RevokeReason, name="revoke_reason_enum"),
        nullable=True,
    )

    user: Mapped["Users"] = relationship(
        "Users",
        backref="sessions",
    )

    __table_args__ = (
        sa.Index("ix_auth_sessions_user", "user_id"),
        sa.Index("ix_auth_sessions_last_seen", "last_seen_at"),
    )


class RefreshTokens(IntPKMixin, Base):

    user_id: Mapped[int] = mapped_column(
        sa.BigInteger,
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # уникальный идентификатор токена и его "семьи" ротаций
    jti: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        unique=True,
    )
    family_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        index=True,
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        index=True,
    )

    # храним хеш токена
    token_hash: Mapped[str] = mapped_column(
        sa.String(64),
        unique=True,
    )

    issued_at: Mapped["datetime"] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
    )
    expires_at: Mapped["datetime"] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
    )
    used_at: Mapped["datetime | None"] = mapped_column(
        sa.DateTime(timezone=True),
    )
    revoked_at: Mapped["datetime | None"] = mapped_column(
        sa.DateTime(timezone=True),
    )
    revoked_reason: Mapped[RevokeReason | None] = mapped_column(
        sa.Enum(RevokeReason, name="revoke_reason_enum"),
        nullable=True,
    )

    # для цепочки ротаций (каким jti заменён)
    replaced_by_jti: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
    )

    user: Mapped["Users"] = relationship(
        "Users",
        backref="refresh_tokens",
    )

    __table_args__ = (
        sa.Index("ix_refresh_tokens_user", "user_id"),
        sa.Index("ix_refresh_tokens_session", "session_id"),
        sa.Index("ix_refresh_tokens_family", "family_id"),
    )
