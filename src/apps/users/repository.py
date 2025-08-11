from typing import Optional

from infra.repository import SQLAlchemyRepository

from apps.users.models import Users


class UsersRepo(SQLAlchemyRepository[Users]):
    model = Users

    # ---- READ ----
    async def get_by_email(self, email: str) -> Optional[Users]:
        return await self.one_or_none(self.model.email == email)

    async def email_exists(self, email: str) -> bool:
        return await self.exists(self.model.email == email)

    async def list_active(
        self,
        *,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[Users]:
        return await self.list(
            self.model.is_active.is_(True),
            order_by=(self.model.id.desc(),),
            limit=limit,
            offset=offset,
        )

    # ---- CREATE ----
    async def create_user(
        self,
        *,
        email: str,
        hashed_password: str,
        full_name: str | None = None,
        is_superuser: bool = False,
    ) -> Users:
        return await self.create(
            {
                "email": email,
                "hashed_password": hashed_password,
                "full_name": full_name,
                "is_superuser": is_superuser,
            }
        )

    # ---- UPDATE ----
    async def set_password(self, user_id: int, hashed_password: str) -> Users:
        return await self.update_by_id(user_id, {"hashed_password": hashed_password})

    async def activate(self, user_id: int) -> Users:
        return await self.update_by_id(user_id, {"is_active": True})

    async def deactivate(self, user_id: int) -> Users:
        return await self.update_by_id(user_id, {"is_active": False})

    async def set_superuser(self, user_id: int, value: bool = True) -> Users:
        return await self.update_by_id(user_id, {"is_superuser": value})

    # ---- DELETE ----
    async def delete_by_email(self, email: str) -> int:
        return await self.delete_where(self.model.email == email)
