from typing import Any, ClassVar, Generic, Iterable, Optional, Sequence, TypeVar

import sqlalchemy as sa
from sqlalchemy.engine import Result
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import LoaderOption

T = TypeVar("T")  # ORM-модель


class NotFoundError(Exception):
    pass


class SQLAlchemyRepository(Generic[T]):
    """Базовый репозиторий без commit/rollback. Работает поверх AsyncSession."""

    model: ClassVar[type[T]]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ---- CREATE ----
    async def create(self, data: dict[str, Any]) -> T:
        stmt = sa.insert(self.model).values(**data).returning(self.model)
        res: Result = await self.session.execute(stmt)
        return res.scalar_one()

    # ---- READ ----
    async def get_by_id(
        self, id_: int, *, options: Sequence[LoaderOption] = ()
    ) -> Optional[T]:
        stmt = sa.select(self.model).where(self.model.id == id_)
        for opt in options:
            stmt = stmt.options(opt)
        res: Result = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def one_or_none(
        self,
        *where: sa.sql.ClauseElement,
        options: Sequence[LoaderOption] = (),
    ) -> Optional[T]:
        stmt = sa.select(self.model).where(*where)
        for opt in options:
            stmt = stmt.options(opt)
        res: Result = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def list(
        self,
        *where: sa.sql.ClauseElement,
        options: Sequence[LoaderOption] = (),
        order_by: Sequence[sa.ColumnElement[Any]] | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[T]:
        stmt = sa.select(self.model).where(*where)
        if order_by:
            stmt = stmt.order_by(*order_by)
        if limit is not None:
            stmt = stmt.limit(limit)
        if offset is not None:
            stmt = stmt.offset(offset)
        for opt in options:
            stmt = stmt.options(opt)
        res: Result = await self.session.execute(stmt)
        return list(res.scalars())

    async def count(self, *where: sa.sql.ClauseElement) -> int:
        stmt = sa.select(sa.func.count()).select_from(self.model).where(*where)
        res: Result = await self.session.execute(stmt)
        return int(res.scalar_one())

    async def exists(self, *where: sa.sql.ClauseElement) -> bool:
        exists_stmt = (
            sa.select(sa.literal(True)).where(*where).select_from(self.model).limit(1)
        )
        res: Result = await self.session.execute(exists_stmt)
        return res.scalar_one_or_none() is True

    # ---- UPDATE ----
    async def update_by_id(self, id_: int, data: dict[str, Any]) -> T:
        stmt = (
            sa.update(self.model)
            .where(self.model.id == id_)
            .values(**data)
            .returning(self.model)
        )
        res: Result = await self.session.execute(stmt)
        obj = res.scalar_one_or_none()
        if obj is None:
            raise NotFoundError(f"{self.model.__name__} id={id_} not found")
        return obj

    async def update_where(
        self, data: dict[str, Any], *where: sa.sql.ClauseElement
    ) -> list[T]:
        stmt = sa.update(self.model).where(*where).values(**data).returning(self.model)
        res: Result = await self.session.execute(stmt)
        return list(res.scalars())

    # ---- DELETE ----
    async def delete_by_id(self, id_: int) -> None:
        stmt = sa.delete(self.model).where(self.model.id == id_)
        res = await self.session.execute(stmt)
        if res.rowcount == 0:
            raise NotFoundError(f"{self.model.__name__} id={id_} not found")

    async def delete_where(self, *where: sa.sql.ClauseElement) -> int:
        stmt = sa.delete(self.model).where(*where)
        res = await self.session.execute(stmt)
        return int(res.rowcount or 0)
