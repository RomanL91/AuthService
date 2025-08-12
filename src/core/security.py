from passlib.context import CryptContext


class PasswordHasher:
    """
    Обёртка над passlib с единственной схемой bcrypt.
    ✓ hash()        — хеширует пароль
    ✓ verify()      — проверяет пароль; поддерживает мягкую миграцию с plaintext
    ✓ needs_rehash()— сигналит, что хеш стоит пересоздать (например, подняли rounds)
    """

    def __init__(self, rounds: int = 12) -> None:
        self.ctx = CryptContext(
            schemes=["bcrypt"],
            deprecated="auto",
            bcrypt__rounds=rounds,
        )

    @staticmethod
    def _looks_like_bcrypt(value: str) -> bool:
        # bcrypt-хеши начинаются на $2a$ / $2b$ / $2y$
        return isinstance(value, str) and value.startswith("$2")

    def hash(self, raw_password: str) -> str:
        return self.ctx.hash(raw_password)

    def verify(self, raw_password: str, stored: str) -> bool:
        # Мягкая миграция: если в БД лежит «сырой» пароль — сравниваем напрямую
        if not stored or not self._looks_like_bcrypt(stored):
            return raw_password == stored
        return self.ctx.verify(raw_password, stored)

    def needs_rehash(self, stored: str) -> bool:
        # Для plaintext всегда True — перехешируем при первом успешном логине
        if not stored or not self._looks_like_bcrypt(stored):
            return True
        return self.ctx.needs_update(stored)


# Экземпляр
pwd_hasher = PasswordHasher()
