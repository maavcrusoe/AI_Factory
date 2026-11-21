# 009: Fase 3, claim, heartbeat, release y skill `/factory`

Fecha: 2026-11-21. Estado: implementada en rama `factory/fase-3` (PR a `main`).

## Decisiones
- **Estados**: el trabajo reclamado pasa a `CLAIMED`. La cola son los items en `QUEUED`. `release` y la caducidad devuelven a `QUEUED`.
- **Dueño y latido en la fila**: `work_items.owner` (email), `claimed_at`, `last_heartbeat_at`, `heartbeat_state`, `heartbeat_message`. Sin tabla nueva que apunte a `work_items`.
- **Bloqueo**: `SELECT ... FOR UPDATE` por id en claim, heartbeat, release y eventos. Se decide en Python y se hace un único commit. El perdedor de una carrera recibe `409 "ya cogido por <nombre>"`.
- **Caducidad**: job en segundo plano (`CLAIM_EXPIRY_ENABLED`, independiente del sondeo de trackers). Usa `skip_locked` y recomprueba la condición con la fila bloqueada. Plazo `HEARTBEAT_TIMEOUT_SECONDS` = 1800 por defecto. El reloj se inyecta (`now`) para tests.
- **Latido**: no genera evento de auditoría (evita llenar la tabla); guarda solo el último estado y mensaje. Los logs van en `work_item_events` vía `POST /events`.
- **Etiqueta "taken by"**: el claim la escribe en el hub; el release y la caducidad la quitan. La sincronización de Fase 2 la empuja al remoto en el siguiente sondeo. El hub gana.
- **Tokens por desarrollador**: `fct_` + 256 bits aleatorios. En BD solo SHA-256 (`developer_tokens.token_hash`, único). Se muestran una vez al crearlos. Se revocan con `DELETE /api/v1/tokens/{id}`.
- **Identificadores**: `GET /api/v1/projects/{id}/queue` usa el slug del proyecto (el `projectId` de `.factory/config.yaml`).
- **Nombre en etiquetas**: parte local del email, máximo 40 caracteres (`taken by dev1`). Límite de GitHub: 50 caracteres por etiqueta.

## Endpoints
| Método | Ruta | Quién |
|---|---|---|
| GET | `/api/v1/projects/{slug}/queue` | cualquier autenticado |
| POST | `/api/v1/work/{id}/claim` | cualquiera si el item está en cola |
| POST | `/api/v1/work/{id}/heartbeat` | solo el dueño, `{state, message}` |
| POST | `/api/v1/work/{id}/release` | solo el dueño, `{reason}` |
| POST | `/api/v1/work/{id}/events` | solo el dueño, `{kind ≤40, message ≤2000, detail ≤4000 chars}` |
| POST/GET | `/api/v1/tokens` | el propio usuario |
| DELETE | `/api/v1/tokens/{id}` | el propio usuario |

## Fuera de alcance (Fase 3)
- Endpoint de completar trabajo (Fase 4).
- Sincronización inmediata de la etiqueta al reclamar: llega en el siguiente sondeo (hasta 60 s).
- Límite de intentos y reparto por prioridad.

## Riesgos conocidos
- Varios hilos de API: el job de caducidad corre en un hilo por proceso. Con varios procesos, `skip_locked` evita trabajo doble.
- El nombre de la etiqueta usa la parte local del email: dos devs con la misma parte local en dominios distintos colisionarían.
