import uvicorn
from contextlib import asynccontextmanager

from fastapi import FastAPI

from core.settings import settings
from core.db_manager import DataBaseManager


@asynccontextmanager
async def lifespan(app: FastAPI):
    # старт приложения: создаём engine + фабрику сессий
    app.state.db = DataBaseManager(
        url=settings.DATABASE.url, echo=settings.DATABASE.ECHO
    )
    try:
        yield
    finally:
        # закрываем пул соединений
        await app.state.db.dispose()


app = FastAPI(title="Auth Service", lifespan=lifespan)


@app.get("/")
async def start_test():
    return {"message": "3, 2, 1, Start! Service Auth!"}


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.SERVICE_HOST,
        port=settings.SERVICE_PORT,
        reload=settings.SERVICE_RELOAD,
    )
