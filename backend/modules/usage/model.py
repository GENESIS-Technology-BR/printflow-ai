from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database.connection import Base


class PrinterUsageDaily(Base):
    __tablename__ = "printer_usage_daily"
    __table_args__ = (
        UniqueConstraint(
            "company_id",
            "printer_id",
            "usage_date",
            name="uq_printer_usage_daily_company_printer_date",
        ),
        Index(
            "ix_printer_usage_daily_company_date",
            "company_id",
            "usage_date",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies_v2.id"),
        index=True,
        nullable=False,
    )
    printer_id: Mapped[int] = mapped_column(
        ForeignKey("printers.id"),
        index=True,
        nullable=False,
    )
    usage_date: Mapped[date] = mapped_column(
        Date,
        index=True,
        nullable=False,
    )

    # Snapshot diario: relatorios historicos continuam corretos mesmo que
    # nome, IP, unidade ou setor da impressora mudem depois.
    printer_uuid: Mapped[str] = mapped_column(String(36), nullable=False)
    ip: Mapped[str] = mapped_column(String(45), nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    custom_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    hostname: Mapped[str | None] = mapped_column(String(255), nullable=True)
    manufacturer: Mapped[str | None] = mapped_column(String(100), nullable=True)
    model: Mapped[str | None] = mapped_column(String(180), nullable=True)
    serial: Mapped[str | None] = mapped_column(String(180), nullable=True)
    unit_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    sector_name: Mapped[str | None] = mapped_column(String(120), nullable=True)

    opening_page_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    closing_page_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    pages_printed: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    anomaly_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    last_anomaly_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )