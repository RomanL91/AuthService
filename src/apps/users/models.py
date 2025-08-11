from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column


from core.models_mixins import Base, IntPKMixin, TimestampMixin, ActiveFlagMixin


class Users(IntPKMixin, TimestampMixin, ActiveFlagMixin, Base):

    email: Mapped[str] = mapped_column(
        sa.String(255),
        unique=True,
        nullable=False,
        index=True,
    )

    hashed_password: Mapped[str] = mapped_column(
        sa.String(255),
        nullable=False,
    )

    full_name: Mapped[str | None] = mapped_column(
        sa.String(255),
        nullable=True,
    )

    is_superuser: Mapped[bool] = mapped_column(
        sa.Boolean,
        nullable=False,
        server_default=sa.text("false"),
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r}>"
