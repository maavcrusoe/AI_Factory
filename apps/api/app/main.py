import logging
import threading
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy.exc import SQLAlchemyError

from app.config import get_settings
from app.db import SessionLocal
from app.routers import admin, approvals, auth, health, inputs, integrations, projects, tokens, webhooks, work
from app.seed import seed_admin, seed_demo_project
from app.services.claims import expire_forever
from app.services.intake import sweep_stuck_items
from app.services.poller import poll_forever
from app.services.retention import purge_forever

logger = logging.getLogger("factory")


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    try:
        seed_admin()
        seed_demo_project()
        with SessionLocal() as db:
            swept = sweep_stuck_items(db)
        if swept:
            logger.warning("Barrido al arrancar: %d items colgados pasados a revisión humana", swept)
    except SQLAlchemyError:
        # Sin DB la API arranca igual: /health informa del fallo.
        logger.warning("No se pudo sembrar el admin: base de datos no disponible")
    stop = threading.Event()
    if get_settings().tracker_polling_enabled:
        threading.Thread(target=poll_forever, args=(stop,), daemon=True).start()
    if get_settings().claim_expiry_enabled:
        threading.Thread(target=expire_forever, args=(stop,), daemon=True).start()
    if get_settings().log_retention_enabled:
        threading.Thread(target=purge_forever, args=(stop,), daemon=True).start()
    yield
    stop.set()


app = FastAPI(title="AI Factory API", version="0.1.0", lifespan=lifespan)
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(inputs.router)
app.include_router(integrations.router)
app.include_router(webhooks.router)
app.include_router(work.router)
app.include_router(tokens.router)
app.include_router(approvals.router)
app.include_router(admin.router)
app.include_router(projects.router)
