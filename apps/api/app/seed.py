from sqlalchemy import select

from app.config import get_settings
from app.db import SessionLocal
from app.models import User
from app.security import hash_password


def seed_admin() -> None:
    """Crea o actualiza el admin con los valores de .env (el .env manda)."""
    settings = get_settings()
    if not (settings.admin_email and settings.admin_password):
        return
    with SessionLocal() as db:
        admin = db.scalar(select(User).where(User.email == settings.admin_email))
        if admin is None:
            admin = User(email=settings.admin_email, role="admin")
            db.add(admin)
        admin.password_hash = hash_password(settings.admin_password)
        admin.role = "admin"
        admin.is_active = True
        db.commit()
