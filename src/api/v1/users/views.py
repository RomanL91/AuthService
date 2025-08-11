from fastapi import APIRouter, status

from apps.users.schemas import UserCreate, UserRead

from api.v1.api_depends import UsersSvcDep, AccessJWT
from api.v1.users.exceptions import CurrentUserNotFoundError, UserInactiveError
from api.v1.users.docs import RegisterPointDoc, MePointDoc


router = APIRouter(tags=["Users"])


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary=RegisterPointDoc.summary,
    description=RegisterPointDoc.description,
    responses=RegisterPointDoc.responses,
    openapi_extra=RegisterPointDoc.openapi_extra,
)
async def register_user(payload: UserCreate, svc: UsersSvcDep):
    user = await svc.register(
        email=payload.email,
        raw_password=payload.password.get_secret_value(),
        full_name=payload.full_name,
    )
    return user


@router.get(
    "/me",
    response_model=UserRead,
    status_code=status.HTTP_200_OK,
    summary=MePointDoc.summary,
    description=MePointDoc.description,
    responses=MePointDoc.responses,
)
async def me(access: AccessJWT, users: UsersSvcDep):
    user_id = int(access["user_id"])
    user = await users.get(user_id)
    if not user:
        raise CurrentUserNotFoundError()
    if not user.is_active:
        raise UserInactiveError()
    return user
