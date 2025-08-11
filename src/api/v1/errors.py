from dataclasses import dataclass
from typing import Callable, Mapping, Type

from fastapi.responses import JSONResponse
from fastapi import FastAPI, APIRouter, Request, status

from api.v1.users.exceptions import (
    EmailAlreadyUsedError,
    UserNotFoundError,
    WrongPasswordError,
    CurrentUserNotFoundError,
    UserInactiveError,
)

from api.v1.auth.exceptions import (
    AuthHeaderMissingError,
    AuthSchemeInvalidError,
    TokenExpiredError,
    TokenInvalidError,
    TokenWrongTypeError,
)


@dataclass(frozen=True)
class ExceptionSpec:
    """Как маппим доменное исключение в HTTP-ответ."""

    status_code: int
    code: str
    message: str
    headers: dict[str, str] | None = None
    use_exc_message: bool = (
        False  # если True — подставим detail из исключения (str(exc)) вместо message
    )


class ExceptionHandlers:

    def __init__(self, specs: Mapping[Type[BaseException], ExceptionSpec]) -> None:
        self._specs = dict(specs)

    @staticmethod
    def _problem(spec: ExceptionSpec, exc: BaseException) -> JSONResponse:
        message = str(exc) if spec.use_exc_message and str(exc) else spec.message
        return JSONResponse(
            status_code=spec.status_code,
            content={"error": {"code": spec.code, "message": message}},
            headers=spec.headers or {},
        )

    def _make_handler(
        self, spec: ExceptionSpec
    ) -> Callable[[Request, BaseException], JSONResponse]:
        async def _handler(_: Request, exc: BaseException) -> JSONResponse:
            return self._problem(spec, exc)

        return _handler

    def register_on_app(self, app: FastAPI) -> None:
        for exc_type, spec in self._specs.items():
            app.add_exception_handler(exc_type, self._make_handler(spec))

    def register_on_router(self, router: APIRouter) -> None:
        for exc_type, spec in self._specs.items():
            router.add_exception_handler(exc_type, self._make_handler(spec))


# Централизованный маппинг
user_errors_handlers = ExceptionHandlers(
    {
        EmailAlreadyUsedError: ExceptionSpec(
            status_code=status.HTTP_409_CONFLICT,
            code="email_taken",
            message="Email already registered",
        ),
        UserNotFoundError: ExceptionSpec(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="invalid_credentials",
            message="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ),
        WrongPasswordError: ExceptionSpec(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="invalid_credentials",
            message="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ),
        CurrentUserNotFoundError: ExceptionSpec(
            status_code=status.HTTP_404_NOT_FOUND,
            code="user_not_found",
            message="User not found",
        ),
        UserInactiveError: ExceptionSpec(
            status_code=status.HTTP_403_FORBIDDEN,
            code="user_inactive",
            message="User is inactive",
        ),
    }
)

auth_errors_handlers = ExceptionHandlers(
    {
        AuthHeaderMissingError: ExceptionSpec(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="not_authenticated",
            message="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        ),
        AuthSchemeInvalidError: ExceptionSpec(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="invalid_auth_scheme",
            message="Invalid authentication scheme",
            headers={"WWW-Authenticate": "Bearer"},
        ),
        TokenExpiredError: ExceptionSpec(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="token_expired",
            message="Token expired.",
            headers={"WWW-Authenticate": "Bearer"},
        ),
        TokenInvalidError: ExceptionSpec(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="invalid_token",
            message="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
            use_exc_message=True,  # покажу текст внутреней ошибки
        ),
        TokenWrongTypeError: ExceptionSpec(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="invalid_token_type",
            message="Invalid token type.",
        ),
    }
)
