# 7. Plan de implementación del MVP

## Estrategia

Construir vertical slices ejecutables. Cada fase debe acabar con Docker Compose funcional, migraciones, tests y documentación.

## Fase 0: base técnica

**Objetivo:** plataforma arrancable.

Entregables:

- Monorepo.
- FastAPI y Next.js.
- PostgreSQL, Temporal y MinIO.
- SQLAlchemy/Alembic.
- Health checks.
- CI.
- OpenTelemetry básico.
- Autenticación local mínima para desarrollo.

Done:

- `docker compose up` levanta todos los servicios.
- API, dashboard, Temporal y almacenamiento responden.
- Migraciones automáticas controladas.

## Fase 1: Intake vertical slice

- Webhook genérico firmado.
- Idempotencia.
- Normalización.
- Provider LLM simulado y uno real configurable.
- JSON schema para clasificación.
- Estados `RECEIVED` a `ACCEPTED/NEEDS_INFORMATION/REJECTED`.
- Inbox y detalle.
- SSE.
- Decisión manual.

## Fase 2: Agentic SDD

- Crear rama/worktree.
- Generar `.factory/specs/{workItemId}`.
- Spec Writer.
- Validación de archivos requeridos.
- Revisión del plan.
- Draft PR tras el primer commit válido.

## Fase 3: Builder

- Interfaz `CodingAgentProvider`.
- Un provider real.
- Worker Docker aislado.
- Streaming de eventos.
- Cancelación, timeout y presupuesto.
- Push limitado a la rama del trabajo.

## Fase 4: Gates y bucle

- Configuración de checks.
- Ejecución de comandos aprobados.
- Logs y artefactos.
- Failure Report.
- Fingerprint de fallos.
- Reintentos y escalado tras límite.

## Fase 5: Reviews

- Review Router.
- Code Reviewer.
- Test Reviewer.
- Salidas estructuradas.
- Findings y severidad.
- Vuelta a Builder o Spec Writer.

## Fase 6: Preview y especialización

- Deploy Provider inicial.
- Playwright, screenshots y trace.
- axe-core.
- Semgrep, Gitleaks y Trivy.
- UI, UX, Accessibility y Security Review cuando corresponda.

## Fase 7: aprobación y merge

- Centro de aprobaciones.
- Optimistic locking.
- Branch protection.
- Sincronización con main.
- Gate final sobre commit exacto.
- Merge Controller separado.
- Auditoría.

## Fase 8: operación

- Métricas completas.
- Notificaciones.
- Retención.
- Backup/restore.
- Runbooks.
- Pruebas de recuperación.

## Criterios de aceptación globales

1. Evento repetido no duplica trabajo.
2. Intake validado contra schema.
3. Needs Information reanuda el mismo workflow.
4. Spec versionada dentro del repositorio.
5. Builder aislado y sin credenciales de merge.
6. Gates reales asociados a commit SHA.
7. Fallo produce Failure Report.
8. Reintentos limitados.
9. Draft PR visible.
10. Preview opcional.
11. Merge solo tras aprobación y gate final.
12. Reinicios no pierden estado.
13. Cancelación funcional.
14. Dashboard en tiempo real.
15. Cada decisión es auditable.

## Primera tarea para el agente de código

Implementar Fase 0 y el siguiente vertical slice de Fase 1:

1. `POST /api/v1/events/generic` con firma HMAC.
2. Idempotency key obligatoria.
3. Persistencia de payload y WorkItem.
4. Workflow Temporal `WorkItemWorkflow`.
5. Intake provider simulado.
6. Estados hasta `ACCEPTED`, `NEEDS_INFORMATION` o `REJECTED`.
7. Lista y detalle en dashboard.
8. SSE de cambios.
9. Tests unitarios e integración.
10. README con arranque y ejemplo `curl`.
