import os
from dataclasses import dataclass


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_first(primary: str, legacy: str, default: str) -> str:
    return os.getenv(primary) or os.getenv(legacy) or default


def _env_bool_compat(primary: str, legacy: str, default: bool) -> bool:
    if os.getenv(primary) is not None:
        return _env_bool(primary, default)
    return _env_bool(legacy, default)


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "TALVOA")
    version: str = os.getenv("APP_VERSION", "0.6.0")
    environment: str = os.getenv("ENVIRONMENT", "development")
    database_url: str = os.getenv(
        "DATABASE_URL",
        "sqlite:///./printflow.db",
    )
    report_utc_offset_hours: int = int(
        _env_first("TALVOA_REPORT_UTC_OFFSET_HOURS", "PRINTFLOW_REPORT_UTC_OFFSET_HOURS", "-3")
    )

    # FREE keeps the application conservative with database writes and makes
    # the resource budget explicit. PAID keeps the same data model and can
    # relax these controls through environment variables.
    infra_mode: str = _env_first("TALVOA_INFRA_MODE", "PRINTFLOW_INFRA_MODE", "FREE").strip().upper()
    heartbeat_write_interval_seconds: int = int(
        _env_first("TALVOA_HEARTBEAT_WRITE_INTERVAL_SECONDS", "PRINTFLOW_HEARTBEAT_WRITE_INTERVAL_SECONDS", "300")
    )
    free_quota_warn_percent: int = int(
        _env_first("TALVOA_FREE_QUOTA_WARN_PERCENT", "PRINTFLOW_FREE_QUOTA_WARN_PERCENT", "60")
    )
    free_quota_optimize_percent: int = int(
        _env_first("TALVOA_FREE_QUOTA_OPTIMIZE_PERCENT", "PRINTFLOW_FREE_QUOTA_OPTIMIZE_PERCENT", "75")
    )
    free_quota_preserve_percent: int = int(
        _env_first("TALVOA_FREE_QUOTA_PRESERVE_PERCENT", "PRINTFLOW_FREE_QUOTA_PRESERVE_PERCENT", "90")
    )
    free_preserve_nonessential_writes: bool = _env_bool_compat(
        "TALVOA_FREE_PRESERVE_NONESSENTIAL_WRITES",
        "PRINTFLOW_FREE_PRESERVE_NONESSENTIAL_WRITES",
        True,
    )

    @property
    def free_infra(self) -> bool:
        return self.infra_mode == "FREE"


settings = Settings()


def quota_guard_level(usage_percent: float | int | None) -> str:
    """Classifica consumo de recurso sem depender do provedor de banco."""
    if usage_percent is None:
        return "unknown"
    usage = max(0.0, float(usage_percent))
    if usage >= settings.free_quota_preserve_percent:
        return "preserve"
    if usage >= settings.free_quota_optimize_percent:
        return "optimize"
    if usage >= settings.free_quota_warn_percent:
        return "warn"
    return "normal"


def allow_nonessential_write(usage_percent: float | int | None) -> bool:
    if not settings.free_infra:
        return True
    if quota_guard_level(usage_percent) != "preserve":
        return True
    return not settings.free_preserve_nonessential_writes
