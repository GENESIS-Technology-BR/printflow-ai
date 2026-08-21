from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database.connection import Base


class OperationalAlert(Base):
    __tablename__ = "operational_alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies_v2.id"), index=True)
    printer_id: Mapped[int | None] = mapped_column(
        ForeignKey("printers.id"), nullable=True, index=True
    )
    event_key: Mapped[str] = mapped_column(String(180), index=True)
    category: Mapped[str] = mapped_column(String(40), index=True)
    severity: Mapped[str] = mapped_column(String(20), index=True)
    title: Mapped[str] = mapped_column(String(220))
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="open", index=True)
    opened_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    acknowledged_by: Mapped[int | None] = mapped_column(
        ForeignKey("users_v2.id"), nullable=True, index=True
    )
