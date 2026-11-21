# 1. Visión y alcance

## Definición

AI Code Factory es una plataforma agnóstica de proveedores que transforma eventos y peticiones de desarrollo en workflows auditables de intake, especificación, implementación, validación, revisión, aprobación, merge y despliegue.

## Problema

Los repositorios reciben issues y comentarios con calidad desigual. Algunas peticiones son precisas; otras son ambiguas, duplicadas, incompletas o técnicamente inviables. Ejecutar directamente un agente de código sobre cualquier texto produce cambios inconsistentes, bucles costosos y riesgos de seguridad.

La plataforma introduce un proceso gobernado:

1. Filtra entradas de forma determinista.
2. Usa un LLM para comprender la intención cuando una regla no basta.
3. Crea una especificación versionada.
4. Construye en un entorno aislado.
5. Ejecuta gates objetivos.
6. Selecciona revisores según el riesgo real.
7. Corrige fallos usando evidencias.
8. Escala a una persona cuando corresponde.
9. Expone todo el ciclo en un dashboard.

## Tipos de entrada

- Issue o comentario de GitHub/GitLab.
- Work Item de Azure DevOps.
- Ticket de Jira.
- Pull request existente.
- Webhook genérico firmado.
- Petición REST.
- Orden creada desde el dashboard.
- Mensaje procedente de Teams o Slack a través de un conector autorizado.

## Resultados posibles del intake

| Resultado | Acción |
|---|---|
| `ACCEPT` | Crear especificación y continuar |
| `NEEDS_INFORMATION` | Preguntar al autor y pausar el mismo workflow |
| `HUMAN_REVIEW` | Esperar clasificación humana |
| `SPLIT` | Proponer o crear subtareas relacionadas |
| `DUPLICATE` | Enlazar el trabajo existente |
| `REJECT` | Cerrar o etiquetar, indicando el motivo |
| `OUT_OF_SCOPE` | Rechazar por política |

## Alcance del MVP

- GitHub como primer Git provider.
- Webhook genérico como entrada neutral.
- Un repositorio por proyecto.
- Intake híbrido: reglas y LLM con salida estructurada.
- Especificación persistente dentro del repositorio.
- Un provider inicial de agente de código.
- Workers Docker aislados.
- Gates configurables.
- Code Review independiente.
- Draft PR, preview opcional y aprobación humana antes del merge.
- Dashboard con inbox, Kanban, timeline, detalle y aprobaciones.
- PostgreSQL, Temporal y MinIO.
- Notificaciones mediante webhook genérico y un canal inicial.

## Fuera del MVP

- Auto-merge generalizado.
- Producción automática.
- Multi-tenant completo.
- Marketplace público de agentes.
- Facturación.
- Ejecución dinámica en varios clústeres.
- Soporte simultáneo inicial para GitHub, GitLab y Azure DevOps.
- Entrenamiento de modelos.

## Criterio de éxito

El MVP es válido cuando una petición autorizada puede recorrer de forma recuperable y auditable:

```text
Webhook -> Intake -> Spec -> Build -> Gate -> Review -> Draft PR
        -> Preview -> Human approval -> Merge
```

sin perder estado tras reinicios y sin entregar al Builder credenciales de merge o producción.
