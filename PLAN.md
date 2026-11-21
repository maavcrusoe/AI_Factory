# Plan de arranque: AI Factory

Estado: borrador. Pendiente de respuestas en `PREGUNTAS.md`.

## 1. Preparar el proyecto (hecho)
- Carpeta, docs originales, memoria, specs, CLAUDE.md.

## 2. Especificar antes de construir
Orden de specs a escribir en `specs/` (una por documento, versionadas):
1. `00-vision.md`: problema, usuarios, éxito (parte de docs 01).
2. `01-requisitos.md`: funcionales y no funcionales del MVP.
3. `02-arquitectura.md`: componentes, límites, interfaces de providers.
4. `03-workflow-estados.md`: estados, transiciones, políticas, reintentos.
5. `04-datos-api.md`: modelo de datos, endpoints, eventos SSE.
6. `05-seguridad.md`: privilegios separados, secretos, aislamiento de workers.
7. `06-fases.md`: fases 0–8 con "done" medible.
8. `07-agentes-skills.md`: agentes y skills de desarrollo (abajo).

## 3. Agentes y skills para construir la plataforma
Agentes (`.claude/agents/`), roles de desarrollo, no confundir con los agentes de la fábrica:
- `spec-writer`: redacta/actualiza specs desde decisiones.
- `backend-builder`: FastAPI, SQLAlchemy, Alembic, Temporal.
- `frontend-builder`: Next.js dashboard.
- `test-engineer`: tests unitarios/integración.
- `reviewer`: revisión independiente (no aprueba su propio trabajo).
Skills (`.claude/skills/`): `new-adr`, `update-memory`, `phase-checklist`, `verify-ui-playwright`.

## 4. Fases de construcción (resumen de docs 07)
F0 base técnica → F1 intake vertical slice → F2 SDD → F3 Builder → F4 Gates → F5 Reviews → F6 Preview → F7 Merge → F8 Operación.
Primera entrega: webhook firmado → WorkItem idempotente → intake simulado → estado en dashboard con SSE.

## 5. Verificación
- Backend: tests + `docker compose up`.
- UI: Playwright (navegar, snapshot, screenshot).
- Código: CodeGraph tras `codegraph init`.
