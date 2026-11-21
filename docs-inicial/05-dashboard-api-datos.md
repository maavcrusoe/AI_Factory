# 5. Dashboard, API y modelo de datos

## Vistas del dashboard

### Overview

- Inputs recibidos.
- Ejecuciones activas.
- Trabajos esperando persona.
- PR creadas y fusionadas.
- Fallos y reintentos.
- Tiempo medio por fase.
- Coste por modelo, proyecto y agente.
- Workers disponibles y ocupados.

### Inbox y Kanban

Columnas alineadas con los estados. Filtros por proyecto, proveedor, riesgo, agente, estado y fecha.

### Pipeline visual

Cada trabajo muestra Intake, Spec, Build, Gate, Reviews, Preview, Approval, Merge y Deployment. Cada nodo abre logs, prompts versionados, modelos, comandos, diff, artefactos, coste y motivo de transición.

### Agentes y workers

- Provider y modelo.
- Trabajo y fase.
- Herramienta activa.
- Duración y última actividad.
- Tokens y coste.
- CPU/RAM cuando esté disponible.
- Acciones: cancelar, pausar, reintentar o escalar.

### Centro de aprobación

- Petición original y normalizada.
- Riesgo, confianza y explicación.
- Especificación.
- Diff.
- Tests y seguridad.
- Capturas y URL de preview.
- Findings.
- Cambios desde la revisión anterior.
- Acciones: aprobar, pedir cambios, rechazar, ejecutar review adicional o cancelar.

## API mínima

```text
POST /api/v1/events/{connector}
POST /api/v1/work-items
GET  /api/v1/work-items
GET  /api/v1/work-items/{id}
GET  /api/v1/work-items/{id}/events
GET  /api/v1/work-items/{id}/artifacts
POST /api/v1/work-items/{id}/approve
POST /api/v1/work-items/{id}/request-changes
POST /api/v1/work-items/{id}/retry
POST /api/v1/work-items/{id}/cancel
POST /api/v1/work-items/{id}/resume
GET  /api/v1/agents
GET  /api/v1/workers
GET  /api/v1/projects
PUT  /api/v1/projects/{id}/policies
GET  /api/v1/events/stream
```

## Entidades

- `Tenant`
- `User`
- `Project`
- `Repository`
- `Connector`
- `WorkItem`
- `WorkItemEvent`
- `WorkflowRun`
- `StageRun`
- `AgentRun`
- `ToolRun`
- `ValidationRun`
- `ReviewRun`
- `Finding`
- `Artifact`
- `FailureReport`
- `ApprovalRequest`
- `ApprovalDecision`
- `Deployment`
- `Notification`
- `UsageRecord`
- `PolicyProfile`

## Requisitos de datos

- UUID/ULID para identificadores internos.
- Timestamps UTC.
- Eventos append-only.
- Optimistic locking para decisiones humanas.
- Idempotency key única por conector y evento.
- Payload original separado del modelo normalizado.
- Artefactos mediante URL firmada y checksum.
- Retención configurable por proyecto.
- Borrado y anonimización con auditoría.

## Tiempo real

Usar SSE inicialmente para:

- Cambio de estado.
- Nuevos logs resumidos.
- Nuevos findings.
- Worker asignado.
- Aprobación solicitada.
- Coste actualizado.

No enviar logs completos mediante SSE. Guardarlos por bloques en el almacenamiento de artefactos y emitir referencias.
