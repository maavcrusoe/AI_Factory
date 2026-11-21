# AI Code Factory

Documentación inicial para construir una fábrica de software dirigida por eventos, basada en **Agentic Spec-Driven Development**, agentes de código intercambiables, validaciones proporcionales al riesgo y aprobaciones humanas configurables.

## Objetivo

Convertir una entrada externa en un cambio de software trazable:

```text
Input -> Intake -> Especificación -> Construcción -> Gates -> Reviews
      -> Draft PR -> Preview/Staging -> Aprobación -> Merge -> Despliegue
```

Las entradas pueden proceder de GitHub, GitLab, Azure DevOps, Jira, una API, un webhook o una interfaz propia. El núcleo desconoce el proveedor concreto gracias a adapters.

## Documentos

1. [Visión y alcance](01-vision-y-alcance.md)
2. [Arquitectura](02-arquitectura.md)
3. [Workflow, estados y políticas](03-workflow-estados-politicas.md)
4. [Agentic SDD, agentes y validaciones](04-agentic-sdd-agentes-validaciones.md)
5. [Dashboard, API y modelo de datos](05-dashboard-api-datos.md)
6. [Seguridad, despliegue y observabilidad](06-seguridad-despliegue-observabilidad.md)
7. [Plan de implementación del MVP](07-plan-implementacion-mvp.md)
8. [Backlog inicial](08-backlog-inicial.md)
9. [Decisiones arquitectónicas](09-decisiones-arquitectonicas.md)
10. [Configuración de ejemplo](10-configuracion-ejemplo.md)

## Principios no negociables

- El intake combina reglas deterministas y comprensión mediante LLM.
- Los resultados de tests los determinan herramientas reales y códigos de salida, no un LLM.
- El LLM sí interpreta requisitos, clasifica dificultad, riesgo y alcance, y evalúa aspectos semánticos.
- Cada trabajo tiene especificación persistente dentro del repositorio.
- Las validaciones se seleccionan según tipo de cambio, riesgo, paths y diff real.
- El Builder no aprueba su propio trabajo.
- Las credenciales de construcción, merge y producción están separadas.
- Una Draft PR se crea pronto y actúa como contenedor visible del trabajo.
- Un fallo de implementación vuelve al Builder; un fallo de especificación vuelve al Spec Writer o a una persona.
- El auto-merge y el despliegue automático dependen de políticas explícitas.
- Todo evento, decisión, artefacto, coste y aprobación es auditable.

## Stack inicial recomendado

- Backend: Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2, Alembic.
- Workflow: Temporal.
- Datos: PostgreSQL 16.
- Artefactos: MinIO o S3.
- Frontend: Next.js, TypeScript, React Flow, TanStack Query, Tailwind y shadcn/ui.
- Tiempo real: Server-Sent Events inicialmente.
- Workers: Docker en el MVP; Kubernetes/OpenShift después.
- Observabilidad: OpenTelemetry, Prometheus, Grafana, Loki y Tempo.

## Primera entrega recomendada

Construir un vertical slice que reciba un webhook firmado, cree un WorkItem idempotente, ejecute el intake, persista la decisión y muestre el estado en tiempo real. No empezar todavía por la ejecución de agentes de código.
