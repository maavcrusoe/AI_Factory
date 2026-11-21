# Tareas

## Fase 0: base del hub
- [ ] Monorepo, `.gitignore`, `.env.example`. Verify: árbol creado.
- [ ] API FastAPI + `/health` + test. Verify: `cd apps/api && pytest`.
- [ ] Postgres (Docker) + Alembic + modelos `projects`, `users`. Verify: `alembic upgrade head`.
- [ ] Dashboard Next.js con página de estado. Verify: Playwright screenshot.
- [ ] Login local mínimo (admin por `.env`). Verify: test de login.
- [ ] `npm run dev` en la raíz levanta api + dashboard. Verify: ambos responden.

## Fase 1: entrada e intake
- [ ] Modelos `WorkItem`, `WorkItemEvent`. Verify: migración.
- [ ] `POST /api/v1/inputs` + idempotencia. Verify: test.
- [ ] Reglas deterministas. Verify: test.
- [ ] `IntakeModel` + cliente Ollama + schema + fallback humano. Verify: tests con mock.
- [ ] Inbox y detalle en dashboard. Verify: Playwright.
- [ ] Decisión manual + SSE. Verify: test + Playwright.

## Fases 2 a 7
Ver tareas en `specs/03` a `specs/08`. Se desglosan al terminar la fase anterior.
