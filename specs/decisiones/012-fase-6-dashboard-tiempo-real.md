# 012: Fase 6, dashboard completo en tiempo real

Fecha: 2026-11-22. Estado: implementada en rama `factory/fase-6` (PR a `main`).

## Decisiones
- **Sin migración**: ningún cambio de esquema. Los campos nuevos del tablero salen de columnas existentes.
- **Proyectos**: `GET /api/v1/projects` devuelve cada proyecto con nº de items por estado. Cualquier autenticado lo lee.
- **Filtros del tablero**: `GET /api/v1/inputs` acepta `status`, `project` (slug), `owner` (email) y `source`. La respuesta (`WorkItemListOut`) añade `project_slug`, `owner`, `last_heartbeat_at` y `heartbeat_state`. El detalle no cambia.
- **Tiempo real de latidos**: un latido no escribe auditoría, así que el SSE no lo veía. El stream ahora también sondea `work_items.updated_at` y emite `change` con `kind: work_updated`. Marca de agua con la hora de la BD y solape de 5 s para latidos que esperaron un bloqueo `FOR UPDATE`.
- **Latido caducado en el navegador**: un latido viejo no genera evento, así que el componente `HeartbeatAge` re-evalúa cada 15 s. Se marca como caducado cuando supera la **mitad** de `heartbeat_timeout_seconds` (por defecto 15 min de 30). Aviso antes de que el claim caduque.
- **Ajustes de solo lectura**: `GET /api/v1/settings` devuelve `log_retention_days` y `heartbeat_timeout_seconds`.
- **Retención de logs**: `LOG_RETENTION_DAYS` (por defecto 30). Un hilo de fondo borra cada hora los artefactos `log` más antiguos. Diffs e informes se conservan porque son la base de las aprobaciones y la auditoría. `LOG_RETENTION_ENABLED=false` desactiva el hilo (tests).
- **Admin de usuarios**: `PATCH /api/v1/users/{id}` cambia rol y activo. Un admin no puede quitarse el rol de admin ni desactivarse (422). Un usuario desactivado pierde también sus tokens `fct_` (ya lo hacía `user_by_api_token`). `UserOut` añade `is_active`.
- **Admin de políticas**: pantalla sobre `GET`/`PUT /api/v1/projects/{slug}/merge-policy` de Fase 5, sin API nueva. Guardar crea una versión nueva.
- **Tablero**: columnas Entrada, En cola, En curso, PR en borrador, Aprobación y Cerrado. Cada estado cae en una única columna (`BOARD_COLUMNS`). Sin arrastrar y soltar.
- **Visor de logs y diffs**: `ArtifactView` colorea las líneas de diff (`+`/`-`/`@@`). Los logs se muestran tal cual.
- **Tipado**: `layout.tsx` usa `{ children: ReactNode }` en lugar de `LayoutProps`, que no existe sin `next typegen`. `tsc --noEmit` pasa.

## Verificación
- pytest API: 110 pasan, 2 saltados (antes 101). Nuevos: `test_dashboard_api.py` (resumen, filtros, PATCH de usuario, ajustes, retención, frame SSE de latido). `test_intake.py` filtra los frames `work_updated` en su comprobación de orden.
- `tsc --noEmit` y `eslint` del dashboard: sin errores.
- Playwright sobre BD local con datos de demo: tablero (columnas y tarjetas), latido caducado resaltado, detalle con diff coloreado y línea de tiempo, usuarios, políticas (guardar crea versión 1 y se restaura a 2), proyectos, y sin scroll horizontal a 390 px.
- Las capturas se guardaron en `.playwright-mcp/` (ignorado por git) y se borraron antes de commitear.

## Fuera de alcance (Fase 6)
- Arrastrar tarjetas entre columnas.
- Retención editable desde la UI: solo variable de entorno.
- Solo se purgan logs; diffs e informes no se borran nunca.
- El tablero muestra como máximo 200 items (límite de la lista existente).
- Filtro de dueño como texto libre (no hay lista de usuarios para no-admins).
- Si un lote de más de 100 items se actualiza dentro de la misma ventana de 5 s, el SSE puede tardar un ciclo en emitir el resto. El cliente recarga igualmente.
- Cambios de rol solo por API de admin desde la pantalla; sin historial de cambios de usuario (queda en log).
