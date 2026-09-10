from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from backend.app.config.settings import settings
from backend.app.database.connection import Base, engine
from backend.app.database import models as database_models
from backend.app.database.migrations import (
    clean_descriptive_printer_serials,
    ensure_printer_columns,
    ensure_printer_company_ip_constraint,
    ensure_company_agent_columns,
    ensure_operational_alert_columns,
    ensure_user_security_columns,
)
from backend.app.routers.health import router as health_router
from backend.modules.auth.model import User
from backend.modules.auth.router import router as auth_router
from backend.modules.companies.model import Company
from backend.modules.companies.router import router as companies_router
from backend.modules.organization.router import router as organization_router
from backend.modules.dashboard.router import router as dashboard_router
from backend.modules.alerts.router import router as alerts_router
from backend.modules.control_center.router import router as control_center_router
from backend.modules.usage.router import router as usage_router
from backend.modules.intelligence.router import router as intelligence_router

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
    ensure_operational_alert_columns(engine)
    ensure_user_security_columns(engine)
    clean_descriptive_printer_serials(engine)
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="Plataforma GENESIS para gestão inteligente de impressão",
    lifespan=lifespan,
)

allowed_origins = [
    "https://printflow-web.onrender.com",
    "https://printflow-m84u.onrender.com",
]

allow_origin_regex = None

if settings.environment.lower() != "production":
    allowed_origins.append("http://localhost:5173")
    allow_origin_regex = r"https://.*\.app\.github\.dev"

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=allow_origin_regex,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "Accept",
        "X-Recovery-Key",
    ],
)


@app.middleware("http")
async def security_headers(
    request: Request,
    call_next,
):
    response = await call_next(request)

    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = (
        "camera=(), microphone=(), geolocation=()"
    )

    if settings.environment.lower() == "production":
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )

    if request.url.path not in {"/docs", "/redoc", "/openapi.json"}:
        response.headers["Content-Security-Policy"] = (
            "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"
        )

    return response

app.include_router(health_router)
app.include_router(auth_router, prefix="/api/v1")
app.include_router(companies_router, prefix="/api/v1")
app.include_router(organization_router, prefix="/api/v1")

if printers_router:
    app.include_router(printers_router, prefix="/api/v1")
app.include_router(usage_router, prefix="/api/v1")
app.include_router(dashboard_router)
app.include_router(alerts_router)
app.include_router(intelligence_router)
app.include_router(control_center_router, prefix="/api/v1")


@app.get("/", tags=["Platform"])
def root():
    return {
        "application": settings.app_name,
        "status": "online",
        "version": settings.version,
    }
