from fastapi import APIRouter, status, HTTPException

from apps.users.schemas import UserCreate, UserRead

from api.v1.api_depends import UsersSvcDep
from api.v1.users.exceptions import EmailAlreadyUsedError


router = APIRouter(tags=["Users"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register_user(payload: UserCreate, svc: UsersSvcDep):
    try:
        user = await svc.register(
            email=payload.email,
            raw_password=payload.password.get_secret_value(),
            full_name=payload.full_name,
        )
        return user
    except EmailAlreadyUsedError:
        # 409 — e-mail уже зарегистрирован
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email already registered"
        )
