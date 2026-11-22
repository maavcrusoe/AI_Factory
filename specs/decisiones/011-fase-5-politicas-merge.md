# 011: Fase 5, políticas, roles y merge

Fecha: 2026-11-22. Estado: implementada en rama `factory/fase-5` (PR a `main`).

## Decisiones
- **Roles**: `admin`, `developer`, `reviewer`. El valor antiguo `member` se migra a `developer` (migración 0006). El admin crea usuarios (`POST /api/v1/users`).
- **Permisos** (`require_role` en `routers/auth.py`, 401 sin sesión, 403 sin rol):
  - `developer` y `admin` usan `/factory`: cola, claim, heartbeat, release, complete, tracker-link, artefactos, eventos y `gate-report`.
  - `reviewer` y `admin` aprueban, piden cambios y mergean (`approve`, `request-changes`, `merge`).
  - Solo `admin` edita la política (`PUT /api/v1/projects/{slug}/merge-policy`), la credencial de merge (`PUT /api/v1/projects/{slug}/merge-credential`) y crea usuarios.
  - Cualquier autenticado lee la cola `GET /api/v1/approvals` y la política.
- **Política versionada** (tabla `merge_policies`, una fila por versión, `UNIQUE(project_id, version)`). Editar = insertar versión nueva; las anteriores son el historial. Sin filas rige la versión 0 por defecto.
- **Política por defecto** (`require_human_always: true`): todo merge pide humano. Se relaja cambiando datos.
- **Reglas del motor** (`app/services/merge_policy.py`, función pura `evaluate`). Exige humano si:
  - `require_human_always`.
  - La dificultad está en `human_if_difficulty` (por defecto `high`).
  - Alguna ruta tocada casa con `sensitive_paths` (globs; `**` cruza directorios).
  - Funcionalidad no planificada (`human_if_unplanned`).
  - El significado del texto está en `human_if_meaning` (por defecto `major` y `dubious`).
  - Faltan datos (dificultad, rutas, planificación, significado, gate o SHA). Un item aceptado a mano sin dificultad siempre pasa por humano.
- **Rutas sensibles**: lista en la BD por proyecto, editable por admin por API. No van en `.factory/config.yaml`.
- **Informe del gate final** (`POST /api/v1/work/{id}/gate-report`, dueño, estado `PR_OPEN` o `FIXING`). Campos: `sha` (40 hex), `result` (`passed`/`failed`), `meaning_change`, `planned`, `touched_paths`, `review_findings`. Cada informe sube `approval_version` y deja evento `gate_reported`. Un informe nuevo sustituye al anterior.
- **Veredicto**: gate `failed` → sigue en su estado. Gate `passed` → política:
  - Humano → `WAITING_HUMAN_MERGE`.
  - Sin humano → `READY_TO_MERGE` y el controlador mergea con actor `system:policy`.
- **Bloqueo optimista**: `approve`, `request-changes` y `merge` exigen `expected_version`. Se toma `FOR UPDATE` (`_locked`), se compara con `approval_version` (`check_version`) y, si no coincide, 409. Cada decisión incrementa la versión. Un informe nuevo también la incrementa, así que una aprobación sobre un SHA anterior queda obsoleta.
- **Merge controlado** (`app/services/merge.py`, único sitio que mergea):
  1. Bloqueo, comprobación de versión y paso a `MERGING` (commit).
  2. Fuera del bloqueo: `get_head_sha` del PR. Si difiere del `gate_sha`, vuelve a `PR_OPEN`, borra el resultado del gate y audita `merge_rejected_sha`.
  3. Si coincide: `mark_ready` (quita borrador) y `merge_pr(pr, sha)`. GitHub también verifica el `sha`.
  4. Éxito → `MERGED` (`merged`). Fallo remoto → vuelve a `READY_TO_MERGE` (`merge_failed`) y 502.
- **Borrador**: el PR de Fase 4 sale en borrador. La API REST de GitHub no cambia el estado de borrador; el controlador lo quita con la mutación GraphQL `markPullRequestReadyForReview` cuando `draft` es verdadero. Pendiente: confirmar contra la documentación oficial (la consulta de docs falló en esta sesión).
- **Credencial de merge separada**: columna `project_integrations.merge_token_encrypted` (Fernet). La fija el admin. Solo la usa el controlador. Se borra al cambiar de proveedor o de repo. La API solo devuelve `has_merge_token`.
- **Cliente** (`.claude/skills/factory`): tras el complete, `_report_final_gate` ejecuta `checks.sh` sobre el HEAD del PR, calcula `touched_paths` con `git diff --name-only origin/main...HEAD` y envía el informe. `MEANING` y `PLANNED` salen de la última ronda del code-reviewer (`code-reviewer.md` los pide). Sin esas líneas: `dubious` y no planificado, es decir, humano.
- **Auditoría**: cada decisión es un `WorkItemEvent` (`gate_reported`, `policy_evaluated`, `approved`, `changes_requested`, `merge_started`, `merged`, `merge_rejected_sha`, `merge_failed`). Cambio de política = nueva fila versionada con `created_by`.
- **Dashboard**: `/approvals` (cola de `WAITING_HUMAN_MERGE`, `READY_TO_MERGE`, `MERGING`) y `/approvals/[id]` (gate, SHA, significado, política y motivos, rutas, hallazgos, diff del último artefacto `diff` como texto en `<pre>`, auditoría, botones aprobar / pedir cambios / mergear). Un 409 muestra "recarga y decide otra vez".

## Verificación
- pytest API: 101 pasan, 2 saltados. Incluye reglas de política (`test_merge_policy.py`), roles, versiones de política, bloqueo optimista, SHA movido, merge sin credencial y credencial solo admin (`test_approvals.py`). El merge va contra un remoto falso (`FakeGitHub`), nunca contra GitHub real.
- `alembic check` sin cambios pendientes. Downgrade y upgrade de 0006 ejecutados.
- Tests del cliente: `python -m unittest discover -s .claude/skills/factory/scripts`, 29 pasan.
- Playwright sobre la BD de desarrollo y el API local: login de revisor, cola, detalle con gate, política, hallazgos y diff, y aprobación (pasa a "Lista para mergear", versión 2, evento `approved`). No se pulsó Mergear.

## Fuera de alcance (Fase 5)
- UI de edición de política y de usuarios (solo API, admin).
- Merge en Azure DevOps: `merge_pr` valida el SHA; `mark_ready` lanza `NotImplementedError`.
- `touched_paths` y `meaning_change` vienen del cliente. Con la política por defecto no importa, pero si se relaja la política, el upgrade es re-derivar las rutas en el servidor desde el PR.
- Un item atascado en `MERGING` tras un corte no se barre al arrancar.
- Tras "pedir cambios" el item queda en `FIXING` y el dev lo retoma a mano.
- Auditoría de creación de usuarios: fuera de eventos de item (queda en log).
- Merge real en meme-demo: no ejecutado (la brief lo prohíbe).
