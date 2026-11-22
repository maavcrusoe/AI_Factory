# 010: Fase 4, pipeline del cliente

Fecha: 2026-11-21. Estado: implementada en rama `factory/fase-4` (PR a `main`).

## Decisiones
- **Orquestador en Python** (`.claude/skills/factory/scripts/pipeline.py`) en la máquina del dev. Llama a `claude -p` una vez por etapa. Es reanudable (estado en disco) y testable. El hub nunca ejecuta agentes.
- **Binario de Claude sobreescribible** con `FACTORY_CLAUDE_BIN`. Los tests usan un stub, sin LLM.
- **Agentes**: `.claude/agents/{planner,builder,code-reviewer,test-reviewer}.md`. Se cargan con `--append-system-prompt-file` desde el repo del factory, no se copian al worktree (no acaban en el PR).
- **Permisos**: `--permission-mode acceptEdits` y `--allowedTools` acotado.
- **Revisores**: dos, `code-reviewer` y `test-reviewer` (resuelve la pregunta abierta de spec 05).
- **Worktrees y estado fuera del clon**: `<padre>/<repo>.factory/` con `worktrees/<id>` y `runs/<id>/`. Así no se ensucia el árbol del proyecto.
- **Rama**: `factory/<id>` desde `origin/main`. El cliente solo empuja ramas `factory/*` y nunca hace merge.
- **Rondas**: gate rojo o revisor con cambios pedidos vuelve al builder. Máximo 3 rondas de builder. `SPEC_PROBLEM` del builder vuelve al planner (máximo 1 vez). Tope alcanzado, sin crédito o límite de uso: `release` con motivo `necesita humano: ...`.
- **Logs y diffs**: tabla `work_artifacts` (migración 0005). Cada subida tiene `client_key` único por item, así un reintento no duplica. Tope de 200 000 caracteres por artefacto. Las transiciones de etapa van como eventos `kind="stage"` en el endpoint de eventos existente.
- **Completar**: `POST /api/v1/work/{id}/complete {prUrl, prNumber}` pasa el item a `PR_OPEN`. La caducidad solo mira `CLAIMED`, así que un item con PR no vuelve a la cola.
- **Enlace al issue**: `POST /api/v1/work/{id}/tracker-link` guarda el issue remoto (para `Closes #N`). Sin esto un item de formulario o API no tiene issue que cerrar.
- **PR**: el cliente abre el PR en borrador con `gh pr create --draft` (sesión `gh` local). No se guarda ni se envía ningún token al hub. Esto se aparta del "flujo hub/adapter" del brief: el adapter de GitHub necesitaría el token guardado en el hub, y el brief prohíbe almacenar tokens. Queda como punto abierto.
- **Heartbeat**: hilo en el orquestador cada 60 s. Antes de reanudar se envía un latido; un 409 significa que se perdió el claim y el proceso se detiene.
- **Cola offline**: las subidas que fallan por red se guardan en `runs/<id>/outbox.jsonl` y se reenvían al reanudar.
- **Fallo sin salida**: antes de liberar se sube `failure_report`.

## Endpoints nuevos
| Método | Ruta | Quién |
|---|---|---|
| POST | `/api/v1/work/{id}/complete` | dueño, item en `CLAIMED` |
| POST | `/api/v1/work/{id}/tracker-link` | cualquier autenticado |
| POST | `/api/v1/work/{id}/artifacts` | dueño, `{stage, round, kind, clientKey, content}` |
| GET | `/api/v1/work/{id}/artifacts` | cualquier autenticado |

## Fuera de alcance (Fase 4)
- Adapter de PR en el hub con token guardado (ver punto de PR).
- Merge y política de aprobación (Fase 5).
- Reviewer de seguridad y UX (solo code y test).
- Sondeo de GitHub en la E2E: el hub no tiene token de integración; el issue se enlaza a mano.

## Riesgos conocidos
- Sin token de integración, el sincronizador de etiquetas no escribe en el remoto para el item de prueba.
- Reintentos de subida con red inestable: la idempotencia depende de `clientKey`, no de transacciones entre cliente y hub.
- `claude -p` consume la cuenta Claude del dev. Un límite de uso libera el item con motivo.
