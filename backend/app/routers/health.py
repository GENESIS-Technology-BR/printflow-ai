from datetime import datetime, timezone

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from backend.app.config.settings import quota_guard_level, settings
from backend.app.database.connection import engine

router = APIRouter(tags=["Health"])


@router.get("/health")
def health():
    database_status = "connected"
    http_status = 200

    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception:
        database_status = "unavailable"
        http_status = 503

    payload = {
        "application": settings.app_name,
        "version": settings.version,
        "environment": settings.environment,
        "status": "healthy" if http_status == 200 else "degraded",
        "infrastructure": {
            "mode": settings.infra_mode,
            "quota_guard": {
                "level": quota_guard_level(None),
                "warn_percent": settings.free_quota_warn_percent,
                "optimize_percent": settings.free_quota_optimize_percent,
                "preserve_percent": settings.free_quota_preserve_percent,
            },
        },
        "database": {"status": database_status},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    return JSONResponse(content=payload, status_code=http_status)
