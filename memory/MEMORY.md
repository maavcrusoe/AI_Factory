# Memoria del proyecto AI Factory

Una línea por hecho, con fecha. Detalles en `memory/<tema>.md`.

- 2026-11-21: Proyecto AI Factory = AI Code Factory, docs base en `docs-inicial/` (11 ficheros, extraídos de AI Factory.zip).
- 2026-11-21: Stack propuesto en docs: Python 3.12/FastAPI, Temporal, Postgres 16, MinIO, Next.js, SSE.
- 2026-11-21: Primera entrega recomendada: Fase 0 + vertical slice de Fase 1 (webhook HMAC → WorkItem → intake simulado → dashboard SSE).
- 2026-11-21: Herramientas pedidas: CodeGraph para código, Playwright para ver cambios en UI.
- 2026-11-21: Decisiones del usuario aún sin tomar; ver `PREGUNTAS.md`.
- 2026-11-21: Repo real: C:\Users\Miguel Angel\Documents\GitHub\AI_Factory (GitHub maavcrusoe/AI_Factory). Proyecto movido allí.
- 2026-11-21: Decidido: equipo, GitHub, FastAPI+Next.js+Postgres, sin MinIO, LLM Ollama interno 192.168.100.6:11434 modelo qwen3.5:4b, empezar Fase 0+1. Ver specs/decisiones/001.
- 2026-11-21: Temporal pendiente de decidir (usuario no lo conoce).
- 2026-11-21: CAMBIO DE MODELO: servidor = hub (inbox, estado, dashboard, intake con Ollama); cada dev con Claude Code ejecuta `/factory` que pide trabajo al hub, lo ejecuta local y reporta estado. Ver specs/decisiones/002. Referencia: zazencodes software-factory-claude-code-v2.
- 2026-11-21: Decidido: sin Temporal (estado en Postgres), logs/diffs en Postgres, sin MinIO, GitHub por token, inputs GitHub+AzureDevOps+form+API, arranque npm run, specs ES/código EN, rama main (dev luego), Linux.
- 2026-11-21: Hub nunca ejecuta agentes; claim primero-gana con etiqueta de usuario; heartbeat con timeout por política; merge por política; cliente = skill+REST (MCP futuro); hub solo red interna; demo = app de memes. Ver specs/decisiones/003.
- 2026-11-21: Repo demo creado: github.com/maavcrusoe/meme-demo (privado). Políticas, roles, heartbeat 30min, etiquetas en specs/decisiones/004.
- 2026-11-21: Specs 00-08 (fases 0-7) escritas en specs/, pendientes de aprobación. Intake qwen con valoración; hub gana en etiquetas (decisiones/005).
- 2026-11-21: Specs aprobadas por el owner. tasks/plan.md y tasks/todo.md creados con valores por defecto asumidos. Siguiente: commit y empezar Fase 0.
- 2026-11-21: Fase 0 implementada en rama factory/fase-0: Postgres 16 solo en Docker, API uv+FastAPI, dashboard Next 16, login admin desde .env. Ver specs/decisiones/006.
- 2026-11-21: Fase 1 implementada en rama factory/fase-1: WorkItem + eventos auditados, POST inputs con idempotencia, intake Ollama qwen3.5:4b (think false, schema, timeout 60 s, fallo -> WAITING_HUMAN_TRIAGE), inbox/detalle/decisión/SSE. Ver specs/decisiones/007.
- 2026-11-21: Fase 1 completa en PR #2: webhook genérico HMAC (WEBHOOK_SECRET, X-Idempotency-Key obligatoria), plazo total 60 s del intake, barrido al arrancar a WAITING_HUMAN_TRIAGE. Ver specs/decisiones/007.
- 2026-11-21: Fase 2 en rama factory/fase-2: GitHubAdapter (sondeo 60 s, probado contra meme-demo), AzureDevOpsAdapter con mocks REST (sin org real, pendiente), sincronización de etiquetas con hub ganando, tokens cifrados con Fernet (TOKEN_ENCRYPTION_KEY). Ver specs/decisiones/008.
- 2026-11-21: Azure DevOps queda para después: no hay org/proyecto aún. Sin pruebas reales; prioridad GitHub y sincronización (aviso del owner).
- 2026-11-21: Fase 3 en rama factory/fase-3: claim/heartbeat/release/eventos con FOR UPDATE, caducidad 30 min con reloj inyectable, tokens fct_ hasheados, skill /factory. Ver specs/decisiones/009.
- 2026-11-21: Fase 4 en rama factory/fase-4: pipeline cliente en .claude/skills/factory/scripts (claude -p por etapa, gate, rondas máx. 3, PR borrador con gh, complete -> PR_OPEN, tabla work_artifacts 0005). Hub local puerto 8010 (8000 ocupado). Ver specs/decisiones/010.
- 2026-11-22: Fase 5 en rama factory/fase-5: roles admin/developer/reviewer (require_role), política de merge versionada por proyecto (default todo humano), gate-report por SHA, bloqueo optimista con expected_version, merge vía RepoAdapter con credencial separada y verificación de SHA. Ver specs/decisiones/011.
- 2026-11-22: Fase 6 en rama factory/fase-6: tablero Kanban con filtros, proyectos, latidos en SSE (work_updated), admin de usuarios y políticas, retención de logs 30 días (LOG_RETENTION_DAYS), tsc del layout corregido. Ver specs/decisiones/012.
- 2026-11-22: Fase 7 en rama factory/fase-7: compose (db, migrate, api, dashboard; red backend interna), /metrics admin, logs JSON, backup/restore probados, rotación de TOKEN_ENCRYPTION_KEY con MultiFernet, runbooks en docs/runbooks/, CI mínima. Ver specs/decisiones/013.
- 2026-11-22: E2E local con meme-demo hecho; PR #6 mergeado desde el dashboard (decisión 014). En Windows usar 127.0.0.1, no localhost, para Postgres.
- 2026-11-22: Rol `viewer` (solo lectura: /metrics + lecturas; 403 en crear entradas, decidir, aprobar, claim, admin) y etiqueta de fábrica retirada del remoto al pasar a REJECTED (hub gana, revierte re-añadidos). Sin migración. Ver specs/decisiones/015.
