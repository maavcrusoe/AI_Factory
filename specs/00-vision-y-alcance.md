# Spec 00: Visión y alcance

## Objetivo
AI Factory es un **hub** siempre encendido (red interna) que recibe peticiones de desarrollo (GitHub, Azure DevOps, formulario, API), las filtra con reglas + LLM (Ollama), las pone en una cola y muestra todo en un dashboard. Los devs ejecutan `/factory` en su Claude Code: el cliente toma trabajo, lo construye en local y reporta estado al hub. Usuarios: equipo de desarrollo (primero 1 tester, luego más).

## Principios
- El hub nunca ejecuta Builder, reviewers ni approver.
- Resultado de tests = scripts (`checks.sh`), no un LLM.
- Genérico: adapters de repo/tracker; no acoplado a GitHub.
- Estado, logs y diffs en PostgreSQL.
- Políticas configurables (merge humano, heartbeat, etc.).
- Todo evento queda auditado.
- Ante duda del LLM, decide un humano.

## Arquitectura
```
Fuentes (GitHub, AzDO, form, API) -> Hub (FastAPI + Postgres + Ollama intake)
Hub <-> Dashboard (Next.js, SSE)
Hub <-REST-> Cliente /factory (Claude Code del dev: planner, builder, gate, reviewers, PR)
```

## Stack
Python 3.12 + FastAPI + SQLAlchemy 2 + Alembic; PostgreSQL 16; Next.js + TypeScript + Tailwind; SSE; Ollama `http://192.168.100.6:11434/api/chat` modelo `qwen3.5:4b`. Sin Temporal, sin MinIO.

## Fuera de alcance (ahora)
Multi-tenant, auto-merge generalizado, producción automática, MCP, Kubernetes, facturación.

## Decisiones
Ver `decisiones/001` a `005`.

## Fases
| Fase | Resultado | Spec |
|---|---|---|
| 0 | Hub + dashboard arrancan | 01 |
| 1 | Entrada -> intake Ollama -> cola | 02 |
| 2 | Adapters GitHub/AzDO y sync de etiquetas | 03 |
| 3 | Claim, heartbeat y skill `/factory` básico | 04 |
| 4 | Pipeline del cliente: build, gate, PR, logs | 05 |
| 5 | Políticas, roles, aprobación y merge | 06 |
| 6 | Dashboard completo en tiempo real | 07 |
| 7 | Operación: Docker, métricas, backups | 08 |

## Criterio de éxito global
Una petición de memes entra por form, GitHub o AzDO; el intake la acepta; un dev con `/factory` la toma, la construye, pasa `checks.sh`, abre PR; el merge respeta la política; todo se ve en el dashboard.
