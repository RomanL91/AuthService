import jwt
from typing import Any, Dict
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from core.settings import settings
from apps.auth.schemas import JWTSchema


class JWTUtil:
    """
    Обёртка над PyJWT (RS256).
    - Читает ключи из SettingsAuth (settings.auth_jwt)
    - Генерирует access/refresh по типу токена
    - Возвращает JWTSchema с метаданными (issued_at/expires_at)
    """

    def __init__(self, auth_settings) -> None:
        self.private_key = auth_settings.private_key_path.read_text()
        self.public_key = auth_settings.public_key_path.read_text()
        self.algorithm = auth_settings.algorithm  # "RS256"
        self.access_token_expire = auth_settings.access_token_expire  # минуты
        self.refresh_token_expire = auth_settings.refresh_token_expire  # минуты
        self.token_type_field = auth_settings.token_type_field  # обычно "type"
        self.access_token_type = auth_settings.access_token_type  # "access"
        self.refresh_token_type = auth_settings.refresh_token_type  # "refresh"

    def _now(self) -> datetime:
        return datetime.now(timezone.utc)

    def _ttl_for_type(self, token_type: str) -> int:
        return (
            self.refresh_token_expire
            if token_type == self.refresh_token_type
            else self.access_token_expire
        )

    def encode_jwt(
        self,
        *,
        user_id: int,
        token_type: str,
        extra: Dict[str, Any] | None = None,
    ) -> "JWTSchema":
        from apps.auth.schemas import (
            JWTSchema,
        )  # локальный импорт, чтобы избежать циклов

        now = self._now()
        exp = now + timedelta(minutes=self._ttl_for_type(token_type))
        payload: Dict[str, Any] = {
            "user_id": user_id,
            self.token_type_field: token_type,
            "iat": now,
            "exp": exp,
        }
        if extra:
            payload.update(extra)

        token_value = jwt.encode(
            payload, key=self.private_key, algorithm=self.algorithm
        )
        return JWTSchema(
            user_id=user_id,
            token=token_value,
            token_type=token_type,
            issued_at=now,
            expires_at=exp,
        )

    def decode_jwt(self, token: str) -> dict:
        try:
            # Требуем exp/iat, aud не используем
            return jwt.decode(
                token,
                key=self.public_key,
                algorithms=[self.algorithm],
                options={"require": ["exp", "iat"], "verify_aud": False},
            )
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired."
            )
        except jwt.InvalidTokenError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid token: {e}"
            )

    def get_type(self, payload: dict) -> str | None:
        return payload.get(self.token_type_field)


# Инициализируем единый util на приложение
jwt_util = JWTUtil(settings.AUTH_JWT)


class JWTBearer(HTTPBearer):
    """
    FastAPI-зависимость, которая:
    - принимает Authorization: Bearer <token>
    - декодит JWT и проверяет тип (access/refresh)
    - возвращает payload (dict)
    """

    def __init__(self, expected_token_type: str, auto_error: bool = True) -> None:
        super().__init__(auto_error=auto_error)
        self.expected_token_type = expected_token_type

    async def __call__(self, request: Request) -> dict:
        credentials: HTTPAuthorizationCredentials = await super().__call__(request)
        if not credentials or credentials.scheme.lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid authentication scheme.",
            )
        payload = jwt_util.decode_jwt(credentials.credentials)
        token_type = jwt_util.get_type(payload)
        if token_type != self.expected_token_type:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid token type.",
            )
        return payload
