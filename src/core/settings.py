import os

from pathlib import Path

from pydantic import BaseModel
from pydantic_settings import BaseSettings

from dotenv import load_dotenv


load_dotenv()  # загрузка переменных окружения


BASE_DIR = Path(__file__).parent.parent


class SettingsDataBase(BaseSettings):
    DB_NAME: str = os.getenv("POSTGRES_DB")
    DB_USER: str = os.getenv("POSTGRES_USER")
    DB_PASSWORD: str = os.getenv("POSTGRES_PASSWORD")
    DB_HOST: str = os.getenv("POSTGRES_HOST")
    DB_PORT: int = os.getenv("POSTGRES_PORT")

    ECHO: int = os.getenv("ECHO")

    @property
    def url(self) -> str:
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"


class SettingsAuth(BaseModel):
    # пути к ключам по умолчанию: ./certs/private.pem, ./certs/public.pem
    private_key_path: Path = BASE_DIR / "certs" / "private.pem"
    public_key_path: Path = BASE_DIR / "certs" / "public.pem"

    algorithm: str = os.getenv("JWT_ALG", "RS256")

    token_type_field: str = os.getenv("JWT_TYPE_FIELD", "type")
    token_type: str = os.getenv("JWT_TOKEN_TYPE", "Bearer")

    access_token_type: str = os.getenv("JWT_ACCESS_TYPE", "access")
    refresh_token_type: str = os.getenv("JWT_REFRESH_TYPE", "refresh")

    # сроки жизни в минутах
    access_token_expire: int = int(os.getenv("JWT_ACCESS_TTL_MIN", "15"))
    refresh_token_expire: int = int(
        os.getenv("JWT_REFRESH_TTL_MIN", str(60 * 24 * 14))
    )  # 14 дней


class Settings(BaseSettings):
    # == базовые настройки запуска сервиса
    SERVICE_HOST: str = os.getenv("SERVICE_HOST")
    SERVICE_PORT: int = os.getenv("SERVICE_PORT")
    SERVICE_RELOAD: int = os.getenv("SERVICE_RELOAD")

    #  == настройки префиксов роутинга
    API_V1_PREFIX: str = "/auth_api/v1"

    # == DataBase
    DATABASE: SettingsDataBase = SettingsDataBase()

    # == JWT
    AUTH_JWT: SettingsAuth = SettingsAuth()


settings = Settings()
