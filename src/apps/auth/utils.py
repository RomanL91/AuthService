import jwt
from typing import Any, Dict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from fastapi import Request
from fastapi.security import HTTPBearer
from fastapi.security.utils import get_authorization_scheme_param

from core.settings import settings
from apps.auth.schemas import JWTSchema

from api.v1.auth.exceptions import (
    AuthHeaderMissingError,
    AuthSchemeInvalidError,
    TokenExpiredError,
    TokenInvalidError,
    TokenWrongTypeError,
)


@dataclass(frozen=True)
class VerifiedToken:
    token: str
    payload: dict


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
        self.algorithm = auth_settings.algorithm
        self.access_token_expire = auth_settings.access_token_expire
        self.refresh_token_expire = auth_settings.refresh_token_expire
        self.token_type_field = auth_settings.token_type_field
        self.access_token_type = auth_settings.access_token_type
        self.refresh_token_type = auth_settings.refresh_token_type

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
            return jwt.decode(
                token,
                key=self.public_key,
                algorithms=[self.algorithm],
                options={"require": ["exp", "iat"], "verify_aud": False},
            )
        except jwt.ExpiredSignatureError:
            raise TokenExpiredError()
        except jwt.InvalidTokenError as e:
            raise TokenInvalidError(str(e))

    def get_type(self, payload: dict) -> str | None:
        return payload.get(self.token_type_field)


# Инициализируем единый util на приложение
jwt_util = JWTUtil(settings.AUTH_JWT)


class JWTBearer(HTTPBearer):
    def __init__(
        self,
        expected_token_type: str,
        *,
        scheme_name: str | None = None,
        auto_error: bool = False,
    ) -> None:
        super().__init__(scheme_name=scheme_name, auto_error=auto_error)
        self.expected_token_type = expected_token_type

    async def __call__(self, request: Request) -> VerifiedToken:
        auth: str | None = request.headers.get("Authorization")
        if not auth:
            raise AuthHeaderMissingError()

        scheme, param = get_authorization_scheme_param(auth)
        if not param:
            raise AuthHeaderMissingError()
        if scheme.lower() != "bearer":
            raise AuthSchemeInvalidError()

        payload = jwt_util.decode_jwt(param)
        token_type = jwt_util.get_type(payload)
        if token_type != self.expected_token_type:
            raise TokenWrongTypeError()

        return VerifiedToken(token=param, payload=payload)
