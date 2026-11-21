# 002 Modelo hub + clientes (2026-11-21)

## Decisión
- **Servidor (hub)**: siempre encendido. FastAPI + Postgres + Next.js. Recibe inputs (GitHub, Azure DevOps, formulario, API/webhook), los normaliza, hace intake (reglas + Ollama qwen3.5:4b), guarda estado, logs y diffs en Postgres. Dashboard global para ver y decidir (triage, aprobaciones). No ejecuta el Builder.
- **Cliente**: cada dev usa su Claude Code. Un comando `/factory` (skill + API/MCP del hub) consulta "¿hay trabajo pendiente para este proyecto?", lo toma (claim), lo ejecuta en local (worktree, agentes, gate) y reporta estado al hub periódicamente (heartbeat) y al terminar.
- Humano decide desde el dashboard: filtrar/rechazar, pedir info, aprobar. La consola del dev también puede enviar cambios de estado al hub.
- Referencia: github.com/zazencodes/zazencodes-season-3/tree/main/src/software-factory-claude-code-v2 (skill orquestador `/factory`, agentes intake/planner/builder/reviewer/approver, gate con checks.sh, jobs con estado, solo `factory/*` ramas, merge solo por un script). Diferencia clave: la cola y el estado viven en el hub, no en issues de GitHub ni en ficheros locales.
- Sin Temporal: máquina de estados propia en Postgres (workflow tras una interfaz).
- Artefactos (logs/diffs) en Postgres. Sin MinIO.
- Workers/cliente en Linux. Arranque inicial con `npm run` / local; Docker después.
- Auth: login propio con roles (merge, triage...) a futuro; ahora solo el owner testea.
- GitHub con token; Azure DevOps y form/API además de GitHub desde el diseño (adapters).
- Specs en español, código e identificadores en inglés. Rama main ahora, dev después.
