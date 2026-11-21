# AI Factory (AI Code Factory)

Plataforma de fábrica de software dirigida por eventos (Agentic Spec-Driven Development). Docs base: `docs-inicial/` (00-README … 10-configuracion-ejemplo).

## Dónde vive cada cosa
- `docs-inicial/`: documentación original (solo lectura, fuente de verdad inicial).
- `specs/`: especificaciones vivas del proyecto. `specs/decisiones/` = ADRs y decisiones tomadas en conversación.
- `memory/`: contexto del proyecto para agentes (`MEMORY.md` índice, una línea por hecho, fecha).
- `PLAN.md`: plan por fases, agentes y skills.
- `PREGUNTAS.md`: dudas abiertas. Al resolverlas, mover la decisión a `specs/decisiones/` y a `memory/MEMORY.md`.
- `.claude/agents/`, `.claude/skills/`: agentes y skills del proyecto.

## Herramientas
- Código: usar CodeGraph (`codegraph_explore`) cuando exista `.codegraph/`. Se indexa con `codegraph init` cuando haya código.
- UI: usar Playwright (MCP `playwright-server`) para ver y verificar cambios del dashboard.

## Reglas
- Toda decisión tomada se registra en `specs/decisiones/` y `memory/MEMORY.md`.
- Spec primero, código después. Fase 0 + vertical slice Fase 1 es lo primero (ver `docs-inicial/07-plan-implementacion-mvp.md`).
