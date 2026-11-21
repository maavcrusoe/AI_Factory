# 8. Backlog inicial

## Epic 1: plataforma base

- ACF-001 Crear monorepo y convenciones.
- ACF-002 Crear Docker Compose.
- ACF-003 Configurar FastAPI.
- ACF-004 Configurar Next.js.
- ACF-005 Configurar PostgreSQL y Alembic.
- ACF-006 Configurar Temporal.
- ACF-007 Configurar MinIO.
- ACF-008 Añadir OpenTelemetry.

## Epic 2: dominio y persistencia

- ACF-020 Definir enums y máquina de estados.
- ACF-021 Implementar WorkItem y WorkItemEvent.
- ACF-022 Implementar repositorios de dominio.
- ACF-023 Añadir outbox para eventos.
- ACF-024 Idempotencia de entradas.

## Epic 3: intake

- ACF-040 Webhook genérico HMAC.
- ACF-041 Normalizador.
- ACF-042 Reglas deterministas previas.
- ACF-043 Schema de salida del LLM.
- ACF-044 FakeIntakeProvider.
- ACF-045 Provider LLM real.
- ACF-046 Needs Information y reanudación.
- ACF-047 Human triage.

## Epic 4: Agentic SDD

- ACF-060 Layout `.factory/specs`.
- ACF-061 Spec Writer.
- ACF-062 Validación de especificación.
- ACF-063 Plan de validación.
- ACF-064 Registro de decisiones.
- ACF-065 Draft PR.

## Epic 5: ejecución

- ACF-080 Workspace manager.
- ACF-081 Worker Docker rootless.
- ACF-082 CodingAgentProvider.
- ACF-083 Provider inicial.
- ACF-084 Streaming de ejecución.
- ACF-085 Cancelación y timeouts.
- ACF-086 Presupuestos.

## Epic 6: calidad y reviews

- ACF-100 Check runner.
- ACF-101 Artefactos y logs.
- ACF-102 Failure Report.
- ACF-103 Fingerprint y límite de reintentos.
- ACF-104 Review Router.
- ACF-105 Code Reviewer.
- ACF-106 Test Reviewer.
- ACF-107 Security Reviewer.
- ACF-108 UI/UX/A11y Reviewers.

## Epic 7: aprobación, merge y despliegue

- ACF-120 Approval Service.
- ACF-121 Centro de aprobación.
- ACF-122 Merge Controller.
- ACF-123 Gate final.
- ACF-124 Deploy Provider.
- ACF-125 Preview environment.
- ACF-126 Runtime validation.
- ACF-127 Rollback.

## Epic 8: operación

- ACF-140 Dashboard Overview.
- ACF-141 Kanban.
- ACF-142 Pipeline visual.
- ACF-143 Vista de agentes.
- ACF-144 Métricas.
- ACF-145 Notificaciones.
- ACF-146 Backup y restore.
- ACF-147 Runbooks.

## Prioridad sugerida

1. ACF-001 a ACF-008.
2. ACF-020 a ACF-024.
3. ACF-040 a ACF-047.
4. ACF-140 y detalle básico.
5. ACF-060 a ACF-065.
6. ACF-080 a ACF-086.
7. ACF-100 a ACF-106.
8. Resto según validación del MVP.
