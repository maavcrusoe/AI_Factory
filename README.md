# AI Factory

Monorepo del hub de AI Factory (ver `specs/` y `PLAN.md`).

- `apps/api`: API FastAPI + SQLAlchemy 2 + Alembic (Python 3.12, uv).
- `apps/dashboard`: dashboard Next.js + TypeScript.
- `docker-compose.yml`: hub completo (PostgreSQL 16, migraciones, API y dashboard).
- `docs/runbooks/`: operación (despliegue, backup y restore, rotación de tokens, items atascados, Ollama, métricas y logs).

## Despliegue con Docker (servidor)

```sh
cp .env.example .env          # rellenar secretos (ver runbook de despliegue)
docker compose up -d --build  # base -> migraciones -> API -> dashboard
```

Procedimiento completo en `docs/runbooks/despliegue.md`.

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

## Skill `/factory` (cliente de los devs)

La skill vive en `.claude/skills/factory/` de este repo. Se instala por copia en cada máquina y en cada repo de cliente.

1. Copiar la carpeta a tu proyecto cliente (por ejemplo `meme-demo`):
   ```sh
   mkdir -p <repo-cliente>/.claude/skills
   cp -r .claude/skills/factory <repo-cliente>/.claude/skills/
   ```
2. Crear `<repo-cliente>/.factory/config.yaml` a partir de `config.example.yaml` (`projectId`, `hubUrl`). Este fichero no lleva secretos.
3. Crear tu token personal en el hub. Inicia sesión y pide el token (se muestra una sola vez):
   ```sh
   TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login -H 'Content-Type: application/json' \
     -d '{"email":"<tu-email>","password":"<tu-password>"}' | sed -n 's/.*"access_token":"\([^"]*\)".*/\1/p')
   curl -s -X POST http://localhost:8000/api/v1/tokens -H "Authorization: Bearer $TOKEN" \
     -H 'Content-Type: application/json' -d '{"name":"mi-portatil"}'
   ```
4. Guardar el valor `token` en la variable de entorno `FACTORY_TOKEN` de tu shell o de tu perfil. Nunca en el repo.
5. En Claude Code, dentro del repo cliente, ejecutar `/factory`.

Para revocar un token: `DELETE /api/v1/tokens/{id}` con tu sesión (`GET /api/v1/tokens` lista los tuyos).

Decisiones y reglas: `specs/decisiones/009-fase-3-claim-heartbeat.md`.
