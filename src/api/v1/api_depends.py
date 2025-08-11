from typing import AsyncIterator, Annotated

from fastapi import Request, Depends

from infra.UoW import UnitOfWork
from apps.users.service import UsersService
from apps.auth.service import AuthService
from apps.auth.utils import JWTBearer, jwt_util


# фабрикаа UoW, которая берёт session_factory из app.state.db и yield’ит UoW
async def get_uow(request: Request) -> AsyncIterator[UnitOfWork]:
    session_factory = request.app.state.db.session_factory
    async with UnitOfWork(session_factory) as uow:
        yield uow


UOWDep = Annotated[UnitOfWork, Depends(get_uow)]


def get_users_service(uow: UOWDep) -> UsersService:
    return UsersService(uow=uow)


UsersSvcDep = Annotated[UsersService, Depends(get_users_service)]


def get_auth_service(uow: UnitOfWork = Depends(get_uow)) -> AuthService:
    return AuthService(uow=uow)


AuthSvcDep = Annotated[AuthService, Depends(get_auth_service)]

AccessJWT = Annotated[dict, Depends(JWTBearer(jwt_util.access_token_type))]
