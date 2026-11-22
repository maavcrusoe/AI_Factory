# Spec 07: Fase 6, dashboard completo

## Objetivo
Un único sitio para ver proyectos, cola, quién trabaja en qué, estado en tiempo real, logs y aprobaciones.

## Pantallas
Proyectos, Kanban por estado, detalle con timeline y logs, aprobaciones, usuarios y políticas (admin).

## Success Criteria
1. Estado y heartbeat visibles en tiempo real (SSE).
2. Filtros por proyecto, usuario, estado y origen.
3. Logs y diff consultables por item.
4. Verificado con Playwright (screenshots).

## Tareas
- [x] Kanban + detalle con timeline.
- [x] Visor de logs/diff.
- [x] Pantallas admin. Verify: Playwright.

## Preguntas abiertas
- Retención de logs en Postgres: resuelta en decisiones/012 (`LOG_RETENTION_DAYS`, 30 días, solo logs).
