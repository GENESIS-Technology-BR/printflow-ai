"""Provision a staging-only TALVOA platform administrator.

Run manually in an isolated staging environment, with environment variables
TALVOA_BOOTSTRAP_EMAIL and TALVOA_BOOTSTRAP_PASSWORD supplied securely.
Never store credentials in the repository or CI logs.
"""
import os

from sqlalchemy.orm import Session

from backend.app.config.settings import settings
from backend.app.database.connection import Base, engine
from backend.modules.auth.model import User
from backend.modules.auth.security import hash_password
from backend.modules.companies.model import Company


def main() -> None:
    if settings.environment.strip().lower() not in {"staging", "homologation"}:
        raise RuntimeError("Bootstrap restricted to staging/homologation")
    if os.getenv("TALVOA_ALLOW_STAGING_BOOTSTRAP") != "true":
        raise RuntimeError("Explicit staging bootstrap opt-in required")
    email = os.environ.get("TALVOA_BOOTSTRAP_EMAIL", "").strip().lower()
    password = os.environ.get("TALVOA_BOOTSTRAP_PASSWORD", "")
    if not email or "@" not in email or len(password) < 16:
        raise RuntimeError("Set a valid bootstrap email and password (16+ chars)")
    Base.metadata.create_all(bind=engine)
    with Session(engine) as db:
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            raise RuntimeError("User already exists; refusing to overwrite credentials or roles")
        company = db.query(Company).filter(Company.name == "TALVOA Homologação").first()
        if company is None:
            company = Company(name="TALVOA Homologação")
            db.add(company)
            db.flush()
        db.add(User(
            company_id=company.id,
            name="Administrador TALVOA Homologação",
            email=email,
            password_hash=hash_password(password),
            role="platform_admin",
            active=True,
        ))
        db.commit()
    print("Staging platform administrator provisioned; no credentials printed")


if __name__ == "__main__":
    main()
