from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.app.config.settings import settings
from backend.app.database.connection import Base, engine
from backend.app.routers.health import router as health_router
from backend.modules.companies.model import Company


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="Plataforma GENESIS para gestão inteligente de impressão",
    lifespan=lifespan,
)

app.include_router(health_router)


@app.get("/", tags=["Platform"])
def root():
    return {
        "application": settings.app_name,
        "status": "online",
        "version": settings.version,
    }
