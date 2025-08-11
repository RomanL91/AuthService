from pydantic import BaseModel, ConfigDict, IPvAnyAddress
from uuid import UUID

from datetime import datetime


class JWTSchema(BaseModel):
    user_id: int
    token: str
    token_type: str
    issued_at: datetime
    expires_at: datetime


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int  # сек для access


class RefreshRequest(BaseModel):
    refresh_token: str


class AccessToken(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int


class JWTPayload(BaseModel):
    sub: int  # user_id
    typ: str  # "access"/"refresh"
    jti: str | None = None
    sid: str | None = None
    fam: str | None = None
    ver: int | None = None
    iat: int
    exp: int


# ==== Сессии пользователя ====


class SessionRead(BaseModel):
    session_id: UUID
    user_agent: str | None
    ip_address: IPvAnyAddress | None
    created_at: datetime
    last_seen_at: datetime | None

    model_config = ConfigDict(from_attributes=True)
