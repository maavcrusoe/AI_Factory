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

## Tareas
- [ ] Agentes planner/builder/reviewer. Verify: ejecución en meme-demo.
- [ ] Script gate y registro de rondas. Verify: gate rojo/verde.
- [ ] Subida de logs/diffs. Verify: visible en dashboard.
- [ ] Apertura de PR vía adapter. Verify: PR draft creada.

## Preguntas abiertas
- Cuántos reviewers (code/test) al inicio.
