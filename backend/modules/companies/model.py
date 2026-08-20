import secrets
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database.connection import Base


class Company(Base):
    __tablename__ = "companies_v2"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    uuid: Mapped[str] = mapped_column(
        String(36), unique=True, index=True, default=lambda: str(uuid4())
    )
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    document: Mapped[str | None] = mapped_column(String(30), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    state: Mapped[str | None] = mapped_column(String(2), nullable=True)
    plan: Mapped[str] = mapped_column(String(30), default="pilot")
    agent_token: Mapped[str] = mapped_column(
        String(100), unique=True, index=True,
        default=lambda: secrets.token_urlsafe(32),
    )
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    agent_last_seen: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    agent_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    agent_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    agent_version: Mapped[str | None] = mapped_column(String(30), nullable=True)
    agent_last_error: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    users = relationship("User", back_populates="company")
