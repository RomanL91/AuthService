import uvicorn

from fastapi import FastAPI

from core.settings import settings


app = FastAPI()


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
