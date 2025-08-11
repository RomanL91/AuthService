from uuid import UUID
from typing import Optional
from datetime import datetime, timezone

import sqlalchemy as sa
from sqlalchemy.engine import Result

from infra.repository import SQLAlchemyRepository
from apps.auth.models import AuthSessions, RefreshTokens, RevokeReason

from api.v1.auth.exceptions import RefreshRotateError, RefreshNotActiveError


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ==========================
#         SESSIONS
# ==========================
class AuthSessionsRepo(SQLAlchemyRepository[AuthSessions]):
    model = AuthSessions

    async def create_session(
        self,
        *,
        user_id: int,
        session_id: UUID,
        user_agent: str | None,
        ip_address: str | None,
        last_seen_at: datetime | None = None,
    ) -> AuthSessions:
        return await self.create(
            {
                "user_id": user_id,
                "session_id": session_id,
                "user_agent": user_agent,
                "ip_address": ip_address,
                "last_seen_at": last_seen_at or _utcnow(),
            }
        )

    async def get_by_session_id(self, session_id: UUID) -> Optional[AuthSessions]:
        return await self.one_or_none(self.model.session_id == session_id)

    async def list_active_by_user(self, user_id: int) -> list[AuthSessions]:
        return await self.find_many(
            self.model.user_id == user_id,
            self.model.revoked_at.is_(None),
            order_by=(self.model.last_seen_at.desc(),),
        )

    async def touch(self, session_id: UUID, when: datetime | None = None) -> int:
        """Обновить last_seen_at. Возвращает число обновлённых строк (0/1)."""
        stmt = (
            sa.update(self.model)
            .where(self.model.session_id == session_id, self.model.revoked_at.is_(None))
            .values(last_seen_at=when or _utcnow())
        )
        res = await self.session.execute(stmt)
        return int(res.rowcount or 0)

    async def revoke_session(
        self,
        session_id: UUID,
        *,
        reason: RevokeReason,
        when: datetime | None = None,
    ) -> int:
        """Пометить сеанс отозванным. Возвращает число обновлённых строк."""
        stmt = (
            sa.update(self.model)
            .where(self.model.session_id == session_id, self.model.revoked_at.is_(None))
            .values(revoked_at=when or _utcnow(), revoked_reason=reason)
        )
        res = await self.session.execute(stmt)
        return int(res.rowcount or 0)

    async def revoke_all_for_user(
        self, user_id: int, *, reason: RevokeReason, when: datetime | None = None
    ) -> int:
        stmt = (
            sa.update(self.model)
            .where(self.model.user_id == user_id, self.model.revoked_at.is_(None))
            .values(revoked_at=when or _utcnow(), revoked_reason=reason)
        )
        res = await self.session.execute(stmt)
        return int(res.rowcount or 0)


# ==========================
#       REFRESH TOKENS
# ==========================
class RefreshTokensRepo(SQLAlchemyRepository[RefreshTokens]):
    model = RefreshTokens

    async def create_refresh(
        self,
        *,
        user_id: int,
        jti: UUID,
        family_id: UUID,
        session_id: UUID,
        token_hash: str,
        issued_at: datetime,
        expires_at: datetime,
    ) -> RefreshTokens:
        return await self.create(
            {
                "user_id": user_id,
                "jti": jti,
                "family_id": family_id,
                "session_id": session_id,
                "token_hash": token_hash,
                "issued_at": issued_at,
                "expires_at": expires_at,
                "used_at": None,
                "revoked_at": None,
                "revoked_reason": None,
                "replaced_by_jti": None,
            }
        )

    async def get_by_jti(self, jti: UUID) -> Optional[RefreshTokens]:
        return await self.one_or_none(self.model.jti == jti)

    async def get_active_by_hash(
        self, token_hash: str, *, now: datetime | None = None
    ) -> Optional[RefreshTokens]:
        now = now or _utcnow()
        return await self.one_or_none(
            self.model.token_hash == token_hash,
            self.model.used_at.is_(None),
            self.model.revoked_at.is_(None),
            self.model.expires_at > now,
        )

    async def revoke_by_jti(
        self, jti: UUID, *, reason: RevokeReason, when: datetime | None = None
    ) -> int:
        stmt = (
            sa.update(self.model)
            .where(self.model.jti == jti, self.model.revoked_at.is_(None))
            .values(revoked_at=when or _utcnow(), revoked_reason=reason)
        )
        res = await self.session.execute(stmt)
        return int(res.rowcount or 0)

    async def revoke_family(
        self, family_id: UUID, *, reason: RevokeReason, when: datetime | None = None
    ) -> int:
        stmt = (
            sa.update(self.model)
            .where(self.model.family_id == family_id, self.model.revoked_at.is_(None))
            .values(revoked_at=when or _utcnow(), revoked_reason=reason)
        )
        res = await self.session.execute(stmt)
        return int(res.rowcount or 0)

    async def revoke_by_session(
        self, session_id: UUID, *, reason: RevokeReason, when: datetime | None = None
    ) -> int:
        stmt = (
            sa.update(self.model)
            .where(self.model.session_id == session_id, self.model.revoked_at.is_(None))
            .values(revoked_at=when or _utcnow(), revoked_reason=reason)
        )
        res = await self.session.execute(stmt)
        return int(res.rowcount or 0)

    async def revoke_all_for_user(
        self, user_id: int, *, reason: RevokeReason, when: datetime | None = None
    ) -> int:
        stmt = (
            sa.update(self.model)
            .where(self.model.user_id == user_id, self.model.revoked_at.is_(None))
            .values(revoked_at=when or _utcnow(), revoked_reason=reason)
        )
        res = await self.session.execute(stmt)
        return int(res.rowcount or 0)

    async def rotate_active(
        self,
        *,
        old_token_hash: str,
        new_jti: UUID,
        new_token_hash: str,
        issued_at: datetime,
        expires_at: datetime,
        now: datetime | None = None,
    ) -> RefreshTokens:
        """
        Атомарно помечает старый refresh как использованный и создаёт новый в той же "семье"/сессии.
        Возвращает ВСТАВЛЕННЫЙ новый RefreshTokens.
        Подразумевается, что вызов идёт внутри одной транзакции (через UoW).
        """
        now = now or _utcnow()

        # 1) Пометить старый как used, получить все его поля (family/session/user)
        upd_stmt = (
            sa.update(self.model)
            .where(
                self.model.token_hash == old_token_hash,
                self.model.used_at.is_(None),
                self.model.revoked_at.is_(None),
                self.model.expires_at > now,
            )
            .values(
                used_at=now,
                replaced_by_jti=new_jti,
                revoked_reason=RevokeReason.ROTATED,
            )
            .returning(self.model)
        )
        upd_res: Result = await self.session.execute(upd_stmt)
        old: RefreshTokens | None = upd_res.scalar_one_or_none()
        if old is None:
            # старый не активен → reuse/expired/unknown
            raise RefreshNotActiveError(
                "Refresh token is not active (used/revoked/expired/unknown)."
            )

        # 2) Вставить новый refresh в ту же семью/сессию/пользователя
        ins_stmt = (
            sa.insert(self.model)
            .values(
                user_id=old.user_id,
                jti=new_jti,
                family_id=old.family_id,
                session_id=old.session_id,
                token_hash=new_token_hash,
                issued_at=issued_at,
                expires_at=expires_at,
                used_at=None,
                revoked_at=None,
                revoked_reason=None,
                replaced_by_jti=None,
            )
            .returning(self.model)
        )
        ins_res: Result = await self.session.execute(ins_stmt)
        new_row = ins_res.scalar_one_or_none()
        if new_row is None:
            # крайне маловероятно, но на всякий случай
            raise RefreshRotateError("Failed to insert new refresh token.")

        return new_row
