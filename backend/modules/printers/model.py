from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Integer, String, UniqueConstraint
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database.connection import Base


class Printer(Base):
    __tablename__ = "printers"
    __table_args__ = (
        UniqueConstraint(
            "company_id",
            "ip",
            name="uq_printers_company_ip",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies_v2.id"),
        index=True
    )

    uuid: Mapped[str] = mapped_column(
        String(36), unique=True, index=True, default=lambda: str(uuid4())
    )
    ip: Mapped[str] = mapped_column(String(45), index=True)
    name: Mapped[str] = mapped_column(String(150), default="Impressora")
    manufacturer: Mapped[str | None] = mapped_column(String(100), nullable=True)
    model: Mapped[str | None] = mapped_column(String(180), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="online")
    source: Mapped[str] = mapped_column(String(30), default="agent")
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    page_count_source: Mapped[str | None] = mapped_column(String(60), nullable=True)
    page_count_confidence: Mapped[int | None] = mapped_column(Integer, nullable=True)
    page_count_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    serial: Mapped[str | None] = mapped_column(String(180), nullable=True)
    serial_source: Mapped[str | None] = mapped_column(String(60), nullable=True)
    serial_confidence: Mapped[int | None] = mapped_column(Integer, nullable=True)
    serial_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    toner_percent: Mapped[int | None] = mapped_column(Integer, nullable=True)
    health_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    health_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_seen: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
