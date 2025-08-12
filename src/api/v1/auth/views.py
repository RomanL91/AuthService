from fastapi import APIRouter, Request, Response, status

from apps.users.schemas import UserLogin
from apps.auth.schemas import TokenPair, SessionRead
from api.v1.api_depends import UsersSvcDep, AuthSvcDep, AccessJWT, RefreshJWT
from api.v1.users.exceptions import UserInactiveError

from api.v1.auth.docs import (
    LoginPointDoc,
    LogoutPointDoc,
    RefreshPointDoc,
    LogoutAllPointDoc,
    SessionsListPointDoc as SessionsDoc,
)


router = APIRouter(tags=["Auth"])


@router.post(
    "/login",
    response_model=TokenPair,
    status_code=status.HTTP_200_OK,
    summary=LoginPointDoc.summary,
    description=LoginPointDoc.description,
    responses=LoginPointDoc.responses,
    openapi_extra=LoginPointDoc.openapi_extra,
)
async def login(
    payload: UserLogin, request: Request, users: UsersSvcDep, auth: AuthSvcDep
):
    user = await users.authenticate(
        email=payload.email,
        raw_password=payload.password.get_secret_value(),
    )
    if not user.is_active:
        raise UserInactiveError()

    # создать сессию и выдать пару
    ua = (request.headers.get("user-agent") or "")[:255]
    ip = request.headers.get("x-forwarded-for", "").split(",")[0].strip() or (
        request.client.host if request.client else None
    )
    pair = await auth.login(user_id=user.id, user_agent=ua, ip_address=ip)
    return pair


@router.post(
    "/refresh",
    response_model=TokenPair,
    status_code=status.HTTP_200_OK,
    summary=RefreshPointDoc.summary,
    description=RefreshPointDoc.description,
    responses=RefreshPointDoc.responses,
)
async def refresh(refresh: RefreshJWT, auth: AuthSvcDep):
    return await auth.rotate(refresh_token=refresh.token)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary=LogoutPointDoc.summary,
    description=LogoutPointDoc.description,
    responses=LogoutPointDoc.responses,
)
async def logout(refresh: RefreshJWT, auth: AuthSvcDep):
    await auth.logout_by_refresh(refresh_token=refresh.token)
    # 204 No Content


@router.post(
    "/logout-all",
    status_code=status.HTTP_204_NO_CONTENT,
    summary=LogoutAllPointDoc.summary,
    description=LogoutAllPointDoc.description,
    responses=LogoutAllPointDoc.responses,
    openapi_extra=LogoutAllPointDoc.openapi_extra,
)
async def logout_all(access: AccessJWT, auth: AuthSvcDep):
    user_id = int(access.payload["user_id"])
    await auth.logout_all(user_id=user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/sessions",
    response_model=list[SessionRead],
    status_code=status.HTTP_200_OK,
    summary=SessionsDoc.summary,
    description=SessionsDoc.description,
    responses=SessionsDoc.responses,
)
async def list_my_sessions(access: AccessJWT, auth: AuthSvcDep):
    user_id = int(access.payload["user_id"])
    items = await auth.list_sessions(user_id=user_id)
    return items
