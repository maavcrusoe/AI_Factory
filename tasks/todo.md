# Tareas

## Fase 0: base del hub
- [x] Monorepo, `.gitignore`, `.env.example`. Verify: árbol creado.
- [x] API FastAPI + `/health` + test. Verify: `cd apps/api && pytest`.
- [x] Postgres (Docker) + Alembic + modelos `projects`, `users`. Verify: `alembic upgrade head`.
- [x] Dashboard Next.js con página de estado. Verify: Playwright screenshot.
- [x] Login local mínimo (admin por `.env`). Verify: test de login.
- [x] `npm run dev` en la raíz levanta api + dashboard. Verify: ambos responden.

## Fase 1: entrada e intake
- [x] Modelos `WorkItem`, `WorkItemEvent`. Verify: migración.
- [x] `POST /api/v1/inputs` + idempotencia. Verify: test.
- [x] Reglas deterministas. Verify: test.
- [x] `IntakeModel` + cliente Ollama + schema + fallback humano. Verify: tests con mock.
- [x] Inbox y detalle en dashboard. Verify: Playwright.
- [x] Decisión manual + SSE. Verify: test + Playwright.
- [x] Webhook genérico con firma HMAC + idempotency key obligatoria. Verify: tests (firma válida/inválida, sin clave, duplicado).
- [x] Plazo total del intake (60 s) -> WAITING_HUMAN_TRIAGE. Verify: test con modelo lento.
- [x] Barrido al arrancar de items en RECEIVED/NORMALIZING/TRIAGE. Verify: test + reinicio real de la API.

## Fases 2 a 7
Ver tareas en `specs/03` a `specs/08`. Se desglosan al terminar la fase anterior.
