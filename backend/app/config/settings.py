import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "Printflow")
    version: str = os.getenv("APP_VERSION", "0.5.1")
    environment: str = os.getenv("ENVIRONMENT", "development")
    database_url: str = os.getenv(
        "DATABASE_URL",
        "sqlite:///./printflow.db",
    )
    report_utc_offset_hours: int = int(
        os.getenv("PRINTFLOW_REPORT_UTC_OFFSET_HOURS", "-3")
    )


settings = Settings()
