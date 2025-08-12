from hashlib import sha256
from uuid import UUID, uuid4
from dataclasses import dataclass

from typing import Optional
from datetime import datetime, timezone

from fastapi import HTTPException

from infra.UoW import UnitOfWork
from apps.auth.utils import jwt_util
from apps.auth.models import RevokeReason, AuthSessions
from api.v1.auth.exceptions import (
    RefreshNotActiveError,
    MalformedRefreshTokenError,
    RefreshReuseDetectedError,
    TokenWrongTypeError,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _hash_refresh(token: str) -> str:
    return sha256(token.encode("utf-8")).hexdigest()


@dataclass
class AuthService:
    uow: UnitOfWork

    # ----- LOGIN -----
    async def login(
        self,
        *,
        user_id: int,
        user_agent: Optional[str],
        ip_address: Optional[str],
    ) -> dict:
        """
        Создаёт сессию (sid), первый refresh (fam/jti), и возвращает пару токенов.
        """
        sid = uuid4()
        fam = uuid4()
        jti = uuid4()

        # 1) создать запись о сессии
        await self.uow.sessions.create_session(
            user_id=user_id,
            session_id=sid,
            user_agent=user_agent,
            ip_address=ip_address,
            last_seen_at=_utcnow(),
        )

        # 2) сгенерить access/refresh (вкладываем sid/fam/jti в payload)
        access = jwt_util.encode_jwt(
            user_id=user_id,
            token_type=jwt_util.access_token_type,
            extra={"sid": str(sid)},
        )

        refresh = jwt_util.encode_jwt(
            user_id=user_id,
            token_type=jwt_util.refresh_token_type,
            extra={"sid": str(sid), "fam": str(fam), "jti": str(jti)},
        )

        # 3) сохранить refresh в БД (только хэш)
        await self.uow.refresh.create_refresh(
            user_id=user_id,
            jti=jti,
            family_id=fam,
            session_id=sid,
            token_hash=_hash_refresh(refresh.token),
            issued_at=refresh.issued_at,
            expires_at=refresh.expires_at,
        )

        # UoW закоммитит при выходе из deps, явный commit не обязателен
        return {
            "access_token": access.token,
            "refresh_token": refresh.token,
            "token_type": "Bearer",
            "expires_in": int((access.expires_at - access.issued_at).total_seconds()),
        }

    # ----- REFRESH (ротация) -----
    async def rotate(self, *, refresh_token: str) -> dict:
        # 1) валидируем и парсим payload
        payload = jwt_util.decode_jwt(refresh_token)

        if payload.get("type") != jwt_util.refresh_token_type:
            raise TokenWrongTypeError()

        try:
            sid = UUID(payload["sid"])
            fam = UUID(payload["fam"])
        except Exception:
            raise MalformedRefreshTokenError()

        uid = int(payload["user_id"])

        # 2) генерим новые токены
        new_jti = uuid4()
        new_refresh = jwt_util.encode_jwt(
            user_id=uid,
            token_type=jwt_util.refresh_token_type,
            extra={"sid": payload["sid"], "fam": payload["fam"], "jti": str(new_jti)},
        )
        new_access = jwt_util.encode_jwt(
            user_id=uid,
            token_type=jwt_util.access_token_type,
            extra={"sid": payload["sid"]},
        )

        # 3) атомарная ротация в БД
        try:
            await self.uow.refresh.rotate_active(
                old_token_hash=_hash_refresh(refresh_token),
                new_jti=new_jti,
                new_token_hash=_hash_refresh(new_refresh.token),
                issued_at=new_refresh.issued_at,
                expires_at=new_refresh.expires_at,
            )
        except RefreshNotActiveError:
            # reuse/отозван — ревок всей семьи + сессии и доменная ошибка
            await self.uow.refresh.revoke_family(
                fam, reason=RevokeReason.REUSE_DETECTED
            )
            await self.uow.sessions.revoke_session(
                sid, reason=RevokeReason.REUSE_DETECTED
            )
            raise RefreshReuseDetectedError()

        # 4) touch last_seen
        await self.uow.sessions.touch(sid)

        return {
            "access_token": new_access.token,
            "refresh_token": new_refresh.token,
            "token_type": "Bearer",
            "expires_in": int(
                (new_access.expires_at - new_access.issued_at).total_seconds()
            ),
        }

    # ----- LOGOUT -----
    async def logout_by_refresh(self, *, refresh_token: str) -> None:
        """Отозвать текущий refresh + пометить сессию как отозванную."""
        payload = jwt_util.decode_jwt(refresh_token)
        if payload.get("type") != jwt_util.refresh_token_type:
            raise HTTPException(status_code=400, detail="Invalid token type")
        try:
            jti = UUID(payload["jti"])
            sid = UUID(payload["sid"])
        except Exception:
            raise HTTPException(status_code=400, detail="Malformed refresh token")

        await self.uow.refresh.revoke_by_jti(jti, reason=RevokeReason.USER_LOGOUT)
        await self.uow.sessions.revoke_session(sid, reason=RevokeReason.USER_LOGOUT)

    async def logout_all(self, *, user_id: int) -> None:
        """Отозвать все refresh и сессии пользователя (глобальный выход)."""
        await self.uow.refresh.revoke_all_for_user(
            user_id, reason=RevokeReason.ADMIN_FORCE
        )
        await self.uow.sessions.revoke_all_for_user(
            user_id, reason=RevokeReason.ADMIN_FORCE
        )

    async def list_sessions(self, *, user_id: int) -> list[AuthSessions]:
        """Активные (не отозванные) сессии пользователя, по убыванию last_seen."""
        return await self.uow.sessions.list_active_by_user(user_id)
