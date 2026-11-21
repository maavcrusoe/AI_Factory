# 6. Seguridad, despliegue y observabilidad

## Modelo de confianza

El contenido de issues, comentarios, archivos y documentación es no confiable y puede contener prompt injection. Debe tratarse como datos, no como instrucciones del sistema.

## Controles mínimos

- Webhooks firmados y protección contra replay.
- RBAC por organización, proyecto y acción.
- Credenciales de corta duración.
- Builder sin acceso a merge ni producción.
- Merge Controller como componente separado.
- Workers rootless y sin privilegios.
- Filesystem temporal.
- Allow-list de red.
- CPU, RAM, disco, tiempo y coste limitados.
- Sanitización de logs.
- Auditoría inmutable de aprobaciones.
- Secretos en Vault, External Secrets Operator o servicio cloud equivalente.
- Políticas y checks protegidos.
- Escaneo de imágenes y dependencias.

## Separación de credenciales

| Componente | Permisos |
|---|---|
| Connector | Leer eventos y publicar comentarios limitados |
| Builder | Clonar, crear rama y push a su rama |
| Reviewer | Lectura de repositorio, diff y artefactos |
| Merge Controller | Merge solo tras policy check |
| Deploy Controller | Desplegar solo al entorno autorizado |
| Dashboard | Invocar acciones según RBAC |

## Aislamiento del worker

- Un workspace por trabajo.
- Una rama por trabajo.
- Un contenedor o Pod por job.
- Usuario no root.
- Sin socket Docker salvo worker especializado y controlado.
- Egress bloqueado por defecto.
- Timeout duro.
- Destrucción del workspace al finalizar, después de publicar artefactos.

## Modos de despliegue

- `never`
- `preview-only`
- `development-auto`
- `staging-auto`
- `production-human`
- `production-auto-low-risk`

`production-auto-low-risk` permanece deshabilitado por defecto.

## Validación de runtime

Después de desplegar:

- Smoke tests.
- Health/readiness.
- Tests funcionales dirigidos.
- Errores de consola y red para web.
- Métricas técnicas.
- Comparación con baseline cuando proceda.
- Rollback automático ante condiciones configuradas.

## Observabilidad

### OpenTelemetry

Toda traza debe incluir:

- `tenant.id`
- `project.id`
- `work_item.id`
- `workflow.id`
- `stage_run.id`
- `agent_run.id`
- `provider`
- `model`
- `commit.sha`

### Métricas

- Duración por fase.
- Cola y concurrencia.
- Tasa de aceptación/rechazo.
- Porcentaje de Needs Information.
- Reintentos por tipo.
- Escalados humanos.
- First-pass success rate.
- Coste y tokens.
- Tiempo hasta aprobación.
- Fallos por herramienta.
- Deployments y rollbacks.

### Logs y trazas

- Logs estructurados JSON.
- Correlation IDs.
- OpenTelemetry Collector.
- Loki para logs.
- Tempo para traces.
- Prometheus y Grafana para métricas.
- Sentry para fallos del frontend/backend.

## Notificaciones

Adapters: Teams, Slack, Discord, email, Telegram, Gotify, Apprise y webhook genérico.

Eventos prioritarios:

- Falta información.
- Baja confianza.
- Riesgo crítico.
- Fallos repetidos.
- Vulnerabilidad alta/crítica.
- Presupuesto excedido.
- Preview disponible.
- Aprobación requerida.
- Merge o despliegue completado.
- Rollback.
