# 015: Rol `viewer` y etiqueta de fábrica en items REJECTED

Fecha: 2026-11-22. Estado: implementado.

## Rol `viewer` (solo lectura)
- Nuevo rol `viewer`. Sin migración: `users.role` es `String(20)` sin restricción (el rol se valida en la API con `Literal`).
- Accede a `GET /metrics` (junto con `admin`) y a los endpoints de lectura que ya abre `current_user` (tablero, detalle, aprobaciones en lectura, proyectos, ajustes, política e integración en lectura).
- No puede: crear entradas (`POST /api/v1/inputs`), decidir intake (`/decision`), aprobar/pedir cambios/mergear (Reviewer), reclamar/heartbeat/completar/gate-report (Developer), administrar usuarios, políticas o integraciones (Admin). Esas dos primeras rutas pasan de `current_user` a `Member` (admin, developer, reviewer).
- `admin` conserva `/metrics`. Developer y reviewer siguen sin acceso a `/metrics` (403).
- Los tokens `fct_` (`/api/v1/tokens`) siguen abiertos a cualquier usuario autenticado: un `viewer` puede crear el token de scrape de Prometheus.
- Dashboard: el rol aparece como "Solo lectura" en la gestión de usuarios. Los botones de acción siguen visibles; la API responde 403. Pendiente (punto abierto): ocultarlos para `viewer`.

## Etiqueta de fábrica en REJECTED
- `desired_managed` (sincronización de etiquetas, decisión 008) no incluye la etiqueta de fábrica si el item está `REJECTED`; sí conserva las `taken by`.
- Vale para rechazo manual y de intake: depende solo del estado. Se aplica en el siguiente ciclo de sondeo/sincronización, no al instante.
- El hub gana: si alguien re-añade la etiqueta en el remoto, el siguiente ciclo la revierte (`label_reverted`). El item sigue `REJECTED`; el re-sondeo no lo reingesta (clave de idempotencia).
- Sin bucles: tras la escritura, `managed_labels` iguala lo deseado y el remoto coincide; el ciclo siguiente no escribe.
- Un rechazo no se deshace con la etiqueta; para reabrir hay que crear una entrada nueva.
