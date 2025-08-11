from typing import Optional

from dataclasses import dataclass

from infra.UoW import UnitOfWork

from apps.users.models import Users

from api.v1.users.exceptions import (
    EmailAlreadyUsedError,
    UserNotFoundError,
    WrongPasswordError,
)


@dataclass
class UsersService:
    uow: UnitOfWork

    # ---- READ ----
    async def get(self, user_id: int) -> Optional[Users]:
        return await self.uow.users.get_by_id(user_id)

    async def get_by_email(self, email: str) -> Optional[Users]:
        return await self.uow.users.get_by_email(email)

    # ---- CREATE / REGISTER ----
    async def register(
        self,
        *,
        email: str,
        raw_password: str,
        full_name: str | None = None,
        is_superuser: bool = False,
        activate: bool = True,  # можно сделать False и требовать верификации email
    ) -> Users:
        if await self.uow.users.email_exists(email):
            raise EmailAlreadyUsedError(email)

        user = await self.uow.users.create_user(
            email=email,
            hashed_password=raw_password,
            full_name=full_name,
            is_superuser=is_superuser,
        )

        if activate and not user.is_active:
            user = await self.uow.users.activate(user.id)

        # Явный commit опционален (UoW сделает авто-commit при выходе),
        # но иногда полезен, если дальше идут внешние вызовы.
        # await self.uow.commit()
        return user

    # ---- AUTH / PASSWORDS ----
    async def authenticate(self, *, email: str, raw_password: str) -> Users:
        user = await self.uow.users.get_by_email(email)
        if not user:
            raise UserNotFoundError(email)
        # if not verify_password(raw_password, user.hashed_password):
        if raw_password != user.hashed_password:
            raise WrongPasswordError()
        return user

    async def change_password(
        self, *, user_id: int, current_password: str, new_password: str
    ) -> Users:
        user = await self.uow.users.get_by_id(user_id)
        if not user:
            raise UserNotFoundError(user_id)
        # if not verify_password(current_password, user.hashed_password):
        if current_password != user.hashed_password:
            raise WrongPasswordError()

        return await self.uow.users.set_password(user_id, new_password)

    # ---- UPDATE PROFILE ----
    async def update_profile(
        self, *, user_id: int, full_name: str | None = None
    ) -> Users:
        user = await self.uow.users.get_by_id(user_id)
        if not user:
            raise UserNotFoundError(user_id)

        data: dict[str, object] = {}
        if full_name is not None:
            data["full_name"] = full_name

        if not data:
            return user
        return await self.uow.users.update_by_id(user_id, data)

    # ---- ADMIN flags ----
    async def set_active(self, *, user_id: int, value: bool) -> Users:
        user = await self.uow.users.get_by_id(user_id)
        if not user:
            raise UserNotFoundError(user_id)
        return await self.uow.users.update_by_id(user_id, {"is_active": value})

    async def set_superuser(self, *, user_id: int, value: bool) -> Users:
        user = await self.uow.users.get_by_id(user_id)
        if not user:
            raise UserNotFoundError(user_id)
        return await self.uow.users.set_superuser(user_id, value)
