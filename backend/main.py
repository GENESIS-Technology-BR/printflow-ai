from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.config.settings import settings
from backend.app.database.connection import Base, engine
from backend.app.database import models as database_models
from backend.app.database.migrations import (
    ensure_printer_columns,
    ensure_printer_company_ip_constraint,
    ensure_company_agent_columns,
)
from backend.app.routers.health import router as health_router
from backend.modules.auth.model import User
from backend.modules.auth.router import router as auth_router
from backend.modules.companies.model import Company
from backend.modules.companies.router import router as companies_router
from backend.modules.dashboard.router import router as dashboard_router

try:
    from backend.modules.printers.model import Printer
    from backend.modules.printers.router import router as printers_router
except ImportError:
    printers_router = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    ensure_printer_columns(engine)
    ensure_printer_company_ip_constraint(engine)
    ensure_company_agent_columns(engine)
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="Plataforma GENESIS para gestão inteligente de impressão",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://printflow-web.onrender.com",
        "http://localhost:5173",
    ],
    allow_origin_regex=r"https://.*\.app\.github\.dev",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(auth_router, prefix="/api/v1")
app.include_router(companies_router, prefix="/api/v1")

if printers_router:
    app.include_router(printers_router, prefix="/api/v1")
app.include_router(dashboard_router)


@app.get("/", tags=["Platform"])
def root():
    return {
        "application": settings.app_name,
        "status": "online",
        "version": settings.version,
    }
