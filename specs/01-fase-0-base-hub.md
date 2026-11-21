# Spec 01: Fase 0, base técnica del hub

## Objetivo
Hub y dashboard arrancables en local, con base de datos migrada y health checks. Sin lógica de negocio aún.

## Tech Stack
Python 3.12, FastAPI, SQLAlchemy 2, Alembic, pytest; PostgreSQL 16; Node 20, Next.js, TypeScript.

## Commands
```
API:        cd apps/api && uvicorn app.main:app --reload --port 8000
Migrations: cd apps/api && alembic upgrade head
Tests API:  cd apps/api && pytest
Dashboard:  cd apps/dashboard && npm run dev      (puerto 3000)
Tests UI:   cd apps/dashboard && npm test
Todo:       npm run dev   (raíz: arranca api + dashboard)
```

## Project Structure
```
apps/api/app/{main.py,config.py,db.py,models/,routers/}
apps/api/migrations/   apps/api/tests/
apps/dashboard/        (Next.js)
specs/  docs-inicial/  memory/  .claude/
.env.example
```

## Code Style
Python tipado, identificadores en inglés, `snake_case`; TS `camelCase`. Specs y docs en español.
```python
@router.get("/health")
def health(db: Session = Depends(get_db)) -> dict[str, str]:
    db.execute(text("select 1"))
    return {"status": "ok"}
```

## Testing Strategy
pytest para API (health, conexión DB). Playwright para verificar la pantalla del dashboard.

## Boundaries
- Always: tests antes de commit, config por `.env`, nada de secretos en git.
- Ask first: nuevas dependencias, cambios de esquema fuera de Alembic.
- Never: commitear `.env`, usar Temporal/MinIO, ejecutar agentes en el hub.

## Success Criteria
1. `GET /health` devuelve 200 con DB conectada.
2. `alembic upgrade head` crea tablas base (`projects`, `users`).
3. Dashboard en :3000 muestra estado de la API.
4. Login local mínimo (usuario admin sembrado por `.env`).
5. `npm run dev` en la raíz levanta ambos.

## Tareas
- [ ] Monorepo y `.env.example`. Verify: árbol creado.
- [ ] API FastAPI + `/health` + test. Verify: `pytest`.
- [ ] Postgres + Alembic + modelos base. Verify: `alembic upgrade head`.
- [ ] Dashboard Next.js con página de estado. Verify: Playwright screenshot.
- [ ] Login local mínimo. Verify: test de login.
- [ ] Script raíz `npm run dev`. Verify: ambos responden.

## Preguntas abiertas
- ¿Postgres instalado en local o en Docker solo para la DB?
