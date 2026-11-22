# Spec 05: Fase 4, pipeline del cliente

## Objetivo
El cliente ejecuta planner, builder, gate y reviewers, abre el PR y sube logs y diffs al hub. Basado en software-factory-claude-code-v2.

## Flujo (en la máquina del dev)
claim -> worktree + rama `factory/<id>` -> planner (spec en `.factory/specs/<id>`) -> builder -> gate (`checks.sh`) -> reviewers -> PR draft -> reporte final.
Fallo de gate vuelve al builder (máx 3 rondas). Fallo de spec vuelve al planner. Tope alcanzado -> `release` con "necesita humano".

## Reglas
- Solo ramas `factory/*`; el cliente no hace merge.
- Logs y diffs se suben al hub (Postgres).
- Los agentes corren con la cuenta Claude del dev.

## Success Criteria
1. Un item de meme-demo llega a PR draft con gate verde.
2. Un fallo produce Failure Report.
3. El dashboard muestra cada etapa, logs y diff.
4. Un corte de red no pierde estado local; se reanuda.

## Decisiones de implementación
Ver `specs/decisiones/010-fase-4-pipeline-cliente.md`. Resumen: orquestador Python con `claude -p --agent` por etapa, tabla `work_artifacts`, endpoint `complete` que pasa a `PR_OPEN`, PR en borrador con `gh` local (sin token en el hub).

## Tareas
- [ ] Agentes planner/builder/code-reviewer/test-reviewer. Verify: ejecución en meme-demo.
- [ ] Script gate y registro de rondas (round-N). Verify: tests de gate y rondas, gate rojo/verde.
- [ ] Subida de logs/diffs al hub. Verify: visible en dashboard.
- [ ] Apertura de PR en borrador con `Closes`. Verify: PR draft creada en meme-demo.
- [ ] Reanudar tras corte desde estado local. Verify: test de reanudación sin segundo claim.

## Preguntas abiertas
- Revisores al inicio: `code-reviewer` y `test-reviewer` (resuelto, ver decisión 010).
- Apertura del PR por el hub con token guardado: no se hace (no se almacenan tokens). Queda como punto abierto para Fase 5.
