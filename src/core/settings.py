import os

from pathlib import Path
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


class Settings(BaseSettings):
    # == базовые настройки запуска сервиса
    SERVICE_HOST: str = os.getenv("SERVICE_HOST")
    SERVICE_PORT: int = os.getenv("SERVICE_PORT")
    SERVICE_RELOAD: int = os.getenv("SERVICE_RELOAD")

    #  == настройки префиксов роутинга
    API_V1_PREFIX: str = "/auth_api/v1"

    # == DataBase
    DATABASE: SettingsDataBase = SettingsDataBase()


settings = Settings()
