import os

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from dotenv import load_dotenv


load_dotenv()  # загрузка переменных окружения


BASE_DIR = Path(__file__).parent.parent


class SettingsDataBase(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )
    DB_NAME: str = os.getenv("POSTGRES_DB")
    DB_USER: str = os.getenv("POSTGRES_USER")
    DB_PASSWORD: str = os.getenv("POSTGRES_PASSWORD")
    DB_HOST: str = os.getenv("POSTGRES_HOST")
    DB_PORT: int = os.getenv("POSTGRES_PORT")

    ECHO: int = os.getenv("ECHO")

    @property
    def url(self) -> str:
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"


class SettingsAuth(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )
    # пути к ключам по умолчанию: ./certs/private.pem, ./certs/public.pem
    private_key_path: Path = BASE_DIR / "certs" / "private.pem"
    public_key_path: Path = BASE_DIR / "certs" / "public.pem"

    algorithm: str = Field(default="RS256", validation_alias="JWT_ALG")

    token_type_field: str = Field(default="type", validation_alias="JWT_TYPE_FIELD")
    token_type: str = Field(default="Bearer", validation_alias="JWT_TOKEN_TYPE")

    access_token_type: str = Field(default="access", validation_alias="JWT_ACCESS_TYPE")
    refresh_token_type: str = Field(
        default="refresh", validation_alias="JWT_REFRESH_TYPE"
    )

    # TTL в минутах (pydantic сам приведёт из строки в int)
    access_token_expire: int = Field(default=15, validation_alias="JWT_ACCESS_TTL_MIN")
    refresh_token_expire: int = Field(
        default=14 * 24 * 60,  # 20160
        validation_alias="JWT_REFRESH_TTL_MIN",
    )


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )
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
