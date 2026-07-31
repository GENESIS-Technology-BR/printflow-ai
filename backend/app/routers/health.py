from datetime import datetime, timezone

from fastapi import APIRouter

from backend.app.config.settings import settings

router = APIRouter(tags=["Health"])


@router.get("/health")
def health():
    return {
        "application": settings.app_name,
        "version": settings.version,
        "environment": settings.environment,
        "status": "healthy",
        "database": {"status": "waiting"},
        "agent": {
            "status": "waiting",
            "connected": 0,
        },
        "companies": {"registered": 0},
        "printers": {"registered": 0},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
