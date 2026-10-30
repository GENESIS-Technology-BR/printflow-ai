"""Partner tenancy models (not yet enabled in production)."""
from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from backend.app.database.connection import Base


class Partner(Base):
    __tablename__ = "partners"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class PartnerMembership(Base):
    __tablename__ = "partner_memberships"
    __table_args__ = (UniqueConstraint("partner_id", "user_id", name="uq_partner_membership"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    partner_id: Mapped[int] = mapped_column(ForeignKey("partners.id"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users_v2.id"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(30), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
