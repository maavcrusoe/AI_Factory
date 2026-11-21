import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy.exc import SQLAlchemyError

from app.routers import auth, health
from app.seed import seed_admin

logger = logging.getLogger("factory")


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    try:
        seed_admin()
    except SQLAlchemyError:
        # Sin DB la API arranca igual: /health informa del fallo.
        logger.warning("No se pudo sembrar el admin: base de datos no disponible")
    yield


app = FastAPI(title="AI Factory API", version="0.1.0", lifespan=lifespan)
app.include_router(health.router)
app.include_router(auth.router)
