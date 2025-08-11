from asyncio import current_task
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
    async_scoped_session,
)


class DataBaseManager:
    def __init__(self, url: str, echo: bool = False) -> None:
        self.engine: AsyncEngine = create_async_engine(
            url=url,
            echo=echo,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
            pool_recycle=1800,
        )
        self.session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
            bind=self.engine,
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
        )

    # === Режим 1: обычная сессия на запрос (рекомендуется) ===
    async def session_dependency(self) -> AsyncIterator[AsyncSession]:
        """
        Dependency для FastAPI:
            async def endpoint(session: AsyncSession = Depends(db_manager.session_dependency)):
                ...
        """
        async with self.session_factory() as session:
            try:
                yield session
            finally:
                await session.close()

    # Вариант с явной транзакцией (commit/rollback автоматически):
    async def transactional_session_dependency(self) -> AsyncIterator[AsyncSession]:
        """
        Откроет транзакцию на время обработки запроса.
        Коммит сделается при отсутствии исключений, иначе rollback.
        """
        async with self.session_factory() as session:
            async with session.begin():
                yield session

    # === Режим 2: scoped session для одного asyncio-таска ===
    def get_scoped_session(self):
        """
        Возвращает прокси на сессию, привязанную к current_task().
        """
        return async_scoped_session(self.session_factory, scopefunc=current_task)

    async def scoped_session_dependency(self):
        scoped = self.get_scoped_session()
        try:
            yield scoped
        finally:
            # remove() — синхронный
            scoped.remove()

    # === Shutdown ===
    async def dispose(self) -> None:
        """Грохнуть пул соединений (вызывать на shutdown приложения)."""
        await self.engine.dispose()
