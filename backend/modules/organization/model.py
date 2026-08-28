from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database.connection import Base


class CompanyUnit(Base):
    __tablename__ = "company_units"
    __table_args__ = (
        UniqueConstraint(
            "company_id",
            "name",
            name="uq_company_units_company_name",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    uuid: Mapped[str] = mapped_column(
        String(36),
        unique=True,
        index=True,
        default=lambda: str(uuid4()),
    )

    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies_v2.id"),
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
    )

    active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
    )


class CompanySector(Base):
    __tablename__ = "company_sectors"
    __table_args__ = (
        UniqueConstraint(
            "unit_id",
            "name",
            name="uq_company_sectors_unit_name",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    uuid: Mapped[str] = mapped_column(
        String(36),
        unique=True,
        index=True,
        default=lambda: str(uuid4()),
    )

    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies_v2.id"),
        index=True,
    )

    unit_id: Mapped[int] = mapped_column(
        ForeignKey("company_units.id"),
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
    )

    active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
    )
