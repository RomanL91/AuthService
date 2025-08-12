class RefreshNotActiveError(Exception):
    """Токен не найден / уже использован / отозван / просрочен."""


class RefreshRotateError(Exception):
    """Не удалось атомарно проставить used_at и/или вставить новый токен."""


class AuthHeaderMissingError(Exception):
    """Нет заголовка Authorization или пустой токен."""


class AuthSchemeInvalidError(Exception):
    """Неверная схема авторизации (ожидаем Bearer)."""


class TokenExpiredError(Exception):
    """Подпись валидна, но токен просрочен."""


class TokenInvalidError(Exception):
    """Невалидный токен (подпись, структура, claims)."""


class TokenWrongTypeError(Exception):
    """Токен корректный, но тип не соответствует ожидаемому (access/refresh)."""


class MalformedRefreshTokenError(Exception):
    """В refresh отсутствуют/битые клеймы (sid/fam/jti) или неверный формат."""


class RefreshReuseDetectedError(Exception):
    """Повторный показ (reuse) уже использованного/отозванного refresh."""
