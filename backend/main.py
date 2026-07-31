from fastapi import FastAPI

from backend.app.config.settings import settings
from backend.app.routers.health import router as health_router

app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="Plataforma GENESIS para gestão inteligente de impressão",
)

app.include_router(health_router)


@app.get("/", tags=["Platform"])
def root():
    return {
        "application": settings.app_name,
        "status": "online",
        "version": settings.version,
    }
