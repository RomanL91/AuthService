from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

# ропозитории приложений
from apps.users.repository import UsersRepo
from apps.auth.repository import AuthSessionsRepo, RefreshTokensRepo


class IUnitOfWork(ABC):
    session: AsyncSession

    @abstractmethod
    async def __aenter__(self) -> "IUnitOfWork": ...
    @abstractmethod
    async def __aexit__(self, exc_type, exc, tb) -> None: ...
    @abstractmethod
    async def commit(self) -> None: ...
    @abstractmethod
    async def rollback(self) -> None: ...


class UnitOfWork(IUnitOfWork):
    """
    UoW на базе SQLAlchemy AsyncSession.
    - Открывает сессию в __aenter__, закрывает в __aexit__
    - Авто-commit при отсутствии исключений, иначе rollback
    - Репозитории создаются лениво и используют единую сессию
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self.session: Optional[AsyncSession] = None

        # ленивые репозитории
        self._users_repo: Optional[UsersRepo] = None
        self._sessions_repo: Optional[AuthSessionsRepo] = None
        self._refresh_repo: Optional[RefreshTokensRepo] = None

    # Репозитории как свойства (ленивая инициализация)
    @property
    def users(self) -> UsersRepo:
        if self._users_repo is None:
            assert self.session is not None, "UoW not entered"
            self._users_repo = UsersRepo(self.session)
        return self._users_repo

    @property
    def sessions(self) -> AuthSessionsRepo:
        assert self.session is not None, "UoW not entered"
        if self._sessions_repo is None:
            self._sessions_repo = AuthSessionsRepo(self.session)
        return self._sessions_repo

    @property
    def refresh(self) -> RefreshTokensRepo:
        assert self.session is not None, "UoW not entered"
        if self._refresh_repo is None:
            self._refresh_repo = RefreshTokensRepo(self.session)
        return self._refresh_repo

    async def __aenter__(self) -> "UnitOfWork":
        self.session = self._session_factory()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        try:
            if exc_type is None:
                await self.session.commit()
            else:
                await self.session.rollback()
        finally:
            await self.session.close()

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()

    @asynccontextmanager
    async def savepoint(self) -> AsyncIterator[None]:
        """
        Вложенная транзакция (SAVEPOINT) для локально-атомарных операций.
        Пример:
            async with uow.savepoint():
                ...
        Проще говоря, чтобы откат данных не прошел по всей транзакции - такой вот контроль.
        """
        trans = await self.session.begin_nested()
        try:
            yield
        except Exception:
            await trans.rollback()
            raise
        else:
            await trans.commit()
