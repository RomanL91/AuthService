from fastapi import APIRouter, HTTPException, Request, Response, status

from apps.users.schemas import UserLogin
from apps.auth.schemas import TokenPair, RefreshRequest, SessionRead
from api.v1.api_depends import UsersSvcDep, AuthSvcDep, AccessJWT
from api.v1.users.exceptions import UserNotFoundError, WrongPasswordError


router = APIRouter(tags=["Auth"])


@router.post("/login", response_model=TokenPair, status_code=status.HTTP_200_OK)
async def login(
    payload: UserLogin, request: Request, users: UsersSvcDep, auth: AuthSvcDep
):
    # 1) аутентификация пользователя
    try:
        user = await users.authenticate(
            email=payload.email,
            raw_password=payload.password.get_secret_value(),
        )
    except (UserNotFoundError, WrongPasswordError):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="User is inactive")

    # 2) создать сессию и выдать пару токенов
    ua = request.headers.get("user-agent")
    ip = request.client.host if request.client else None
    pair = await auth.login(user_id=user.id, user_agent=ua, ip_address=ip)
    return pair


@router.post("/refresh", response_model=TokenPair, status_code=status.HTTP_200_OK)
async def refresh(payload: RefreshRequest, auth: AuthSvcDep):
    try:
        pair = await auth.rotate(refresh_token=payload.refresh_token)
        return pair
    except HTTPException as e:
        # прокидываем как есть (401 reuse/expired, 400 тип не тот)
        raise e
    except Exception:
        raise HTTPException(status_code=500, detail="Cannot refresh token")


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Logout (revoke current session)",
    responses={
        204: {"description": "Logged out"},
        400: {"description": "Invalid token type"},
        401: {"description": "Invalid/expired token"},
    },
)
async def logout(payload: RefreshRequest, auth: AuthSvcDep):
    await auth.logout_by_refresh(refresh_token=payload.refresh_token)
    # 204 No Content


@router.post(
    "/logout-all",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Logout from all devices (revoke all sessions and refresh tokens)",
)
async def logout_all(access: AccessJWT, auth: AuthSvcDep):
    user_id = int(access["user_id"])
    await auth.logout_all(user_id=user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/sessions",
    response_model=list[SessionRead],
    status_code=status.HTTP_200_OK,
    summary="List active sessions of current user",
)
async def list_my_sessions(access: AccessJWT, auth: AuthSvcDep):
    user_id = int(access["user_id"])
    items = await auth.list_sessions(user_id=user_id)
    return items
