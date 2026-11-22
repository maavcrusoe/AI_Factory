# Imagen de la API del hub. Una sola imagen sirve para la API y para el paso de migraciones.
# La ruta /srv/factory/apps/api conserva la profundidad del repo: app/config.py calcula REPO_ROOT con parents[3].
FROM ghcr.io/astral-sh/uv:0.13.9 AS uv
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/srv/factory/apps/api/.venv
COPY --from=uv /uv /usr/local/bin/uv

WORKDIR /srv/factory/apps/api

# Capa de dependencias: solo cambia si cambia uv.lock.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY alembic.ini ./
COPY migrations ./migrations
COPY app ./app

ENV PATH="/srv/factory/apps/api/.venv/bin:${PATH}"

RUN useradd --system --uid 10001 --no-create-home factory \
 && chown -R factory:factory /srv/factory
USER factory

EXPOSE 8000
# Un solo worker: el sondeo, la caducidad de claims y la retención son hilos del proceso.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--proxy-headers", "--no-access-log"]
