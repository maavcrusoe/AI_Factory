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

## Fase 2: adapters de repo/tracker
- [x] Interfaces `TrackerAdapter` y `RepoAdapter`, `GenericAdapter`, registro `ADAPTERS`. Verify: test de adapter nuevo enchufado al sondeo.
- [x] `GitHubAdapter` leer/comentar/etiquetar (+ ramas, PR, diff). Verify: tests con transporte falso y `GITHUB_REAL=1` contra meme-demo.
- [x] `AzureDevOpsAdapter` (REST + PAT). Verify: tests con mock REST. Pendiente de org real (owner: sin org aún).
- [x] Sincronizador de etiquetas (hub gana, marcador de origen). Verify: test de reversión y test sin bucles.
- [x] Tokens por proyecto cifrados (Fernet), nunca en claro ni en logs. Verify: test de BD, logs y API.
- [x] Ingesta por sondeo idempotente hacia el intake de Fase 1. Verify: test de doble sondeo.
- [x] Migración `0003_integraciones_tracker`. Verify: upgrade, downgrade, upgrade, `alembic check`.

## Fase 4: pipeline del cliente
- [x] Agentes `planner`, `builder`, `code-reviewer`, `test-reviewer` en `.claude/agents/`. Verify: ejecución real en meme-demo (ver PR E2E).
- [x] Gate determinista (`gate.py`) con registro por ronda y reglas de rondas (`rounds.py`). Verify: `python -m unittest discover -s .claude/skills/factory/scripts` (25 tests).
- [x] Migración `0005_work_artifacts` + subida de logs/diffs por etapa (idempotente por `client_key`). Verify: upgrade, downgrade, upgrade, `alembic check`, tests de hub.
- [x] Endpoints `complete` (PR_OPEN, fuera de la caducidad), `tracker-link` y artefactos. Verify: `pytest` en `apps/api`.
- [x] PR en borrador con `Closes #N` vía `gh` local (`pr.py`, solo `factory/*`). Verify: PR E2E en meme-demo.
- [x] Reanudar tras corte desde `state.json`, outbox de subidas y latido al reanudar (409 = paro). Verify: test de reanudación y de claim perdido.
- [x] Dashboard: etapas, logs y diffs en el detalle. Verify: Playwright (ver PR).
- [ ] Revisar PR de AI Factory y de meme-demo tras CI/revisiones.

## Fases 3 a 7
Ver tareas en `specs/04` a `specs/08`. Se desglosan al terminar la fase anterior.

## Fase 3: claim, heartbeat y skill `/factory`
- [x] Endpoints claim/heartbeat/release/events con `FOR UPDATE`. Verify: test de concurrencia (falla sin el bloqueo).
- [x] `GET /projects/{id}/queue` y 409 "ya cogido por X". Verify: test HTTP.
- [x] Job de caducidad (30 min, configurable) con reloj simulado. Verify: tests a -1 s, +1 s y con latido.
- [x] Tokens por desarrollador hasheados (SHA-256), revocables. Verify: test de BD sin texto plano, 401 con token inválido o revocado.
- [x] Etiqueta "taken by" en el hub, quitada al liberar o caducar; sincronizada por Fase 2. Verify: test de sincronización (pendiente en remoto real).
- [x] Migración `0004_claims_y_tokens`. Verify: upgrade, downgrade, upgrade y `alembic check`.
- [x] Skill `/factory` (cola + claim + heartbeat + release). Verify: ejecución manual con curl contra la API.
- [x] Dashboard: dueño y latido en el detalle. Verify: Playwright.
- [ ] Probar `/factory` en meme-demo real. Pendiente: requiere token y repo de cliente con `.factory/config.yaml`.

## Fase 5: políticas, roles y merge
- [x] Roles `admin`/`developer`/`reviewer` (`member` migrado) + `require_role` en /factory, aprobaciones y admin. Verify: `test_approvals.py` (403/401).
- [x] Usuarios por admin (`POST /api/v1/users`). Verify: test 201/409/422.
- [x] Política por proyecto versionada (`merge_policies`), default todo-humano, editable por admin. Verify: `test_merge_policy.py` y test HTTP de versiones.
- [x] Motor de política puro (dificultad, rutas sensibles, no planificado, significado, datos que faltan). Verify: tests por regla.
- [x] Informe del gate final por SHA (`gate-report`) y veredicto `WAITING_HUMAN_MERGE` / `READY_TO_MERGE`. Verify: tests HTTP con política por defecto y relajada.
- [x] Aprobación, cambios pedidos y merge con bloqueo optimista (`expected_version`). Verify: test de doble aprobación con misma versión -> 409.
- [x] Merge controlado vía `RepoAdapter` con credencial de merge separada, verificación de SHA y `mark_ready`. Verify: transporte falso (`FakeGitHub`), no GitHub real.
- [x] Auditoría de cada decisión (`WorkItemEvent`). Verify: test de eventos.
- [x] Migración `0006_politicas_roles_merge`. Verify: downgrade/upgrade en conftest, `alembic check`.
- [x] Pantalla `/approvals` y detalle con diff, gate, política y botones. Verify: Playwright (aprobar en BD local, sin merge).
- [x] Cliente: gate final sobre el HEAD del PR y `MEANING`/`PLANNED` en el code-reviewer. Verify: unittest del pipeline (29 pasan).
- [ ] Merge real en meme-demo. No se hace: la brief lo prohíbe.
- [ ] Confirmar contra docs de GitHub que la API de merge rechaza borradores (la consulta de docs falló en esta sesión).
## Fase 6: dashboard completo en tiempo real
- [x] Resumen de proyectos (`GET /api/v1/projects`) y pantalla `/projects`. Verify: `test_dashboard_api.py` + Playwright.
- [x] Tablero Kanban por estado `/board` con filtros proyecto, dueño, origen y estado. Verify: test de filtros + Playwright.
- [x] Latidos en tiempo real: SSE emite `work_updated` por `updated_at`; latido caducado resaltado en cliente. Verify: test SSE + Playwright (latido hace 21 min).
- [x] Detalle con línea de tiempo, visor de logs y diff coloreado. Verify: Playwright.
- [x] Admin de usuarios y roles (`PATCH /api/v1/users/{id}`, sin auto-bloqueo). Verify: tests 200/403/404/422.
- [x] Admin de políticas sobre la API de Fase 5 (guardar = versión nueva). Verify: Playwright (v1 y restaurada a v2).
- [x] Retención de logs `LOG_RETENTION_DAYS` (30 por defecto) y job de limpieza. Verify: `test_retention_deletes_only_old_logs`.
- [x] `GET /api/v1/settings` para la UI. Verify: test de valores por defecto.
- [x] Tipo de `layout.tsx` corregido: `tsc --noEmit` pasa. Verify: tsc y eslint.
- [x] Sin migración (no hay cambios de esquema). Verify: no hay archivo nuevo en `migrations/`.
## Fase 7: operación
- [x] Dockerfile de API (uv, usuario no root, un worker) y de dashboard (standalone). Verify: `docker compose build`.
- [x] `docker-compose.yml`: db, migrate, api, dashboard; healthchecks; red `backend` interna; secretos obligatorios desde `.env`. Verify: `docker compose up -d` y `ps` healthy.
- [x] Migraciones en paso controlado (`migrate`, la API espera a `service_completed_successfully`). Verify: exit 0 en el arranque.
- [x] `scripts/backup.sh` y `scripts/restore.sh`. Verify: backup, DROP, restore; huella íntegra salvo barrido de arranque documentado.
- [x] Prueba de reinicio (`scripts/restart-test.sh`). Verify: huella idéntica tras reiniciar db, api y dashboard.
- [x] `/metrics` Prometheus por proyecto, solo admin. Verify: `test_ops.py` y 401/403/200 en vivo.
- [x] Logs estructurados JSON y middleware de acceso sin query string. Verify: `test_ops.py` y `docker compose logs api`.
- [x] Rotación de `TOKEN_ENCRYPTION_KEY` (`python -m app.ops rotate-token-key`, MultiFernet). Verify: rotación en vivo; clave antigua sola falla.
- [x] Runbooks en `docs/runbooks/`: despliegue, backup-restore, rotacion-tokens, items-atascados, ollama-no-disponible, metricas-y-logs. Verify: revisión manual.
- [x] CI mínima en `.github/workflows/ci.yml` (pytest con Postgres, lint y tsc del dashboard). Verify: checks del PR.
- [ ] Servidor y SO de despliegue. Pendiente: decisión del owner.
- [ ] Recuperación automática de items en `MERGING`. Pendiente.
- [ ] Rol de solo lectura para métricas. Pendiente.
