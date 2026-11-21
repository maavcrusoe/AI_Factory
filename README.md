# AI Factory

Monorepo del hub de AI Factory (ver `specs/` y `PLAN.md`).

- `apps/api`: API FastAPI + SQLAlchemy 2 + Alembic (Python 3.12, uv).
- `apps/dashboard`: dashboard Next.js + TypeScript.
- `docker-compose.yml`: solo PostgreSQL 16 en Docker.

## Puesta en marcha (local)

Requisitos: Docker, Node 20+, Python 3.12, [uv](https://docs.astral.sh/uv/).

```sh
cp .env.example .env          # ajustar APP_SECRET_KEY y ADMIN_PASSWORD (no commitear .env)
npm install                   # concurrently (raíz)
npm --prefix apps/dashboard install
npm run db:up                 # PostgreSQL en Docker
(cd apps/api && uv sync)      # dependencias de la API
npm run migrate               # alembic upgrade head
npm run dev                   # API en :8000 y dashboard en :3000
```

Entrar en http://localhost:3000/login con `ADMIN_EMAIL` y `ADMIN_PASSWORD` del `.env`.
El admin se crea o actualiza al arrancar la API a partir de `.env`.

## Tests

```sh
npm run test:api              # pytest (usa la base factory_test, se crea sola)
```
