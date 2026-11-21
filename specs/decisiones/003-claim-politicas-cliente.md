# 003 Claim, políticas y cliente (2026-11-21)

- El hub NUNCA ejecuta Builder, reviewers ni approver. Solo gestiona entradas, estado, etiquetado y dashboard. Esos agentes corren en la máquina del dev con su propia cuenta de Claude.
- El hub usa Ollama (qwen3.5:4b) para leer el issue, ampliarlo, etiquetarlo y darle contexto; automático.
- Cliente = skill `/factory` + API REST del hub. MCP queda como idea futura.
- Etiquetas: todo issue lleva una etiqueta de fábrica (entra en la cola) y una etiqueta de quién lo atiende ("taken by <user>"). El primero que hace claim gana; el segundo recibe "ya cogido por X".
- Heartbeat: el cliente reporta su último estado. Si no hay reporte durante un tiempo definido por política general, el trabajo vuelve a la cola.
- PR: lo abre el subagente del dev. El merge depende de política (dificultad/impacto): puede quedar pendiente de un revisor humano. Política configurable en la fábrica.
- Genérico: adapters de repo/tracker (GitHub, Azure DevOps, otros). No centrarse solo en GitHub.
- Proyecto local: `.factory/config.yaml` con `projectId` y URL del hub; el dashboard muestra el proyecto en tiempo real.
- Azure DevOps (supuesto, confirmar): hub consulta por API REST con token; los repos se leen vía API/CLI.
- Hub solo en red interna.
- Repo demo: app mínima generadora de memes (texto → imagen/chiste) que entra en la cola.
- Orden: Fase 0 (hub+dashboard) y Fase 1 (entrada → intake Ollama → cola), luego cliente `/factory`.
