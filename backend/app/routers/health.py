from datetime import datetime, timezone

from fastapi import APIRouter

from backend.app.config.settings import quota_guard_level, settings

router = APIRouter(tags=["Health"])


@router.get("/health")
def health():
    return {
        "application": settings.app_name,
        "version": settings.version,
        "environment": settings.environment,
        "status": "healthy",
        "infrastructure": {
            "mode": settings.infra_mode,
            "quota_guard": {
                "level": quota_guard_level(None),
                "warn_percent": settings.free_quota_warn_percent,
                "optimize_percent": settings.free_quota_optimize_percent,
                "preserve_percent": settings.free_quota_preserve_percent,
            },
        },
        "database": {"status": "waiting"},
        "agent": {
            "status": "waiting",
            "connected": 0,
        },
        "companies": {"registered": 0},
        "printers": {"registered": 0},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
