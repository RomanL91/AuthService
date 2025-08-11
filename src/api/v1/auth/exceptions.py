class RefreshNotActiveError(Exception):
    """Токен не найден / уже использован / отозван / просрочен."""


class RefreshRotateError(Exception):
    """Не удалось атомарно проставить used_at и/или вставить новый токен."""
