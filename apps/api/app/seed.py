from sqlalchemy import select

from app.config import get_settings
from app.db import SessionLocal
from app.models import Project, User
from app.security import hash_password

DEMO_PROJECT = {"slug": "meme-demo", "name": "Demo de memes"}


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


def seed_demo_project() -> None:
    """Proyecto de demo del hub (idempotente)."""
    with SessionLocal() as db:
        if db.scalar(select(Project).where(Project.slug == DEMO_PROJECT["slug"])) is None:
            db.add(Project(**DEMO_PROJECT))
            db.commit()
