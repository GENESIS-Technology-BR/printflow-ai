import os

from backend.app.database.connection import SessionLocal
from backend.modules.auth.model import User
from backend.modules.auth.security import hash_password
from backend.modules.companies.model import Company


def apply_admin_recovery_from_env() -> bool:
    company_name = os.getenv("PRINTFLOW_RECOVERY_COMPANY", "").strip()
    email = os.getenv("PRINTFLOW_RECOVERY_EMAIL", "").strip().lower()
    password = os.getenv("PRINTFLOW_RECOVERY_PASSWORD", "")

    if not company_name or not email or len(password) < 12:
        return False

    db = SessionLocal()
    try:
        company = (
            db.query(Company)
            .filter(Company.name == company_name)
            .first()
        )
        if company is None:
            raise RuntimeError("Recovery company not found")

        users = (
            db.query(User)
            .filter(
                User.company_id == company.id,
                User.active.is_(True),
                User.role.in_(("admin", "platform_admin")),
            )
            .all()
        )
        if len(users) != 1:
            raise RuntimeError(
                "Recovery requires exactly one active admin user"
            )

        user = users[0]
        user.email = email
        user.password_hash = hash_password(password)
        user.session_version += 1
        db.commit()
        return True
    finally:
        db.close()
