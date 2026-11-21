# 9. Decisiones arquitectónicas iniciales

## ADR-001: Temporal como motor de workflow

**Decisión:** usar Temporal para workflows largos, reintentos, señales humanas y recuperación.

**Consecuencia:** añade infraestructura y curva de aprendizaje, pero evita implementar manualmente una máquina distribuida de estados.

## ADR-002: PostgreSQL como fuente de verdad

**Decisión:** persistir estado funcional y auditoría en PostgreSQL.

**Consecuencia:** Redis se limita a caché y presencia; MinIO/S3 almacena artefactos grandes.

## ADR-003: intake híbrido

**Decisión:** ejecutar reglas deterministas antes del LLM y aplicar políticas después de la clasificación.

**Motivo:** reducir coste y evitar que la interpretación del modelo sobrepase restricciones explícitas.

## ADR-004: especificaciones versionadas

**Decisión:** guardar `.factory/specs/{workItemId}` en la rama del trabajo.

**Motivo:** conservar contrato, tareas, validación y decisiones junto al código.

## ADR-005: Draft PR temprana

**Decisión:** crear Draft PR después del primer commit válido.

**Motivo:** centralizar diff, checks, conversación, preview y trazabilidad.

## ADR-006: validación proporcional

**Decisión:** el Review Router selecciona validaciones según tipo, riesgo, paths y diff.

**Motivo:** una modificación cosmética no necesita el mismo pipeline que autenticación o infraestructura.

## ADR-007: providers intercambiables

**Decisión:** abstraer agentes, modelos, Git, despliegues y notificaciones.

**Motivo:** evitar acoplamiento a Claude Code, Codex, GitHub u OpenShift.

## ADR-008: separación de privilegios

**Decisión:** Builder, Merge Controller y Deploy Controller usan identidades diferentes.

**Motivo:** reducir impacto ante prompt injection o compromiso del worker.

## ADR-009: aprobación humana en el MVP

**Decisión:** todo merge requiere una persona inicialmente.

**Motivo:** obtener datos de calidad y calibrar políticas antes de permitir auto-merge.

## ADR-010: SSE antes que WebSocket

**Decisión:** utilizar SSE para actualizaciones del dashboard en el MVP.

**Motivo:** la mayor parte del tráfico es servidor a cliente y SSE simplifica reconexión y operación.
