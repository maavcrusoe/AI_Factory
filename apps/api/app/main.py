import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy.exc import SQLAlchemyError

from app.db import SessionLocal
from app.routers import auth, health, inputs, webhooks
from app.seed import seed_admin, seed_demo_project
from app.services.intake import sweep_stuck_items

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
    yield


app = FastAPI(title="AI Factory API", version="0.1.0", lifespan=lifespan)
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(inputs.router)
app.include_router(webhooks.router)
