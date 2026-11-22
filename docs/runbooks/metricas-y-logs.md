# Métricas y logs

## Métricas (Prometheus)

Endpoint: `GET /metrics` en la API, formato de texto Prometheus. Se calcula desde PostgreSQL en cada
petición: los valores sobreviven a reinicios y no dependen de la memoria de un proceso.

**Acceso: `admin` y `viewer`.** Sin cabecera → 401; con un token de developer o reviewer → 403. El rol `viewer` (solo lectura) es el adecuado para el scrape: lee `/metrics` y las vistas del dashboard, y no puede aprobar, reclamar, crear entradas ni administrar. No exponer la API
más allá de la red interna sin un proxy que añada filtros.

| Métrica | Tipo | Etiquetas | Significado |
|---|---|---|---|
| `factory_work_items` | gauge | `project`, `status` | Items por estado |
| `factory_queue_size` | gauge | `project` | Items en `QUEUED` |
| `factory_claims_active` | gauge | `project` | Items en `CLAIMED` |
| `factory_heartbeat_expiries_total` | counter | `project` | Claims caducados por falta de latido (evento `heartbeat_expired`) |
| `factory_errors_total` | counter | `project`, `kind` | Eventos de error: `intake_failed`, `merge_failed`, `startup_sweep` |
| `factory_intake_decisions` | gauge | `project`, `decision` | Items por decisión actual del intake |

Los counters salen de `work_item_events`: no se pierden al reiniciar, pero tampoco se reinician. Para
tasas, usa `rate()` en Prometheus.

### Configurar el scrape

Crea un usuario `viewer` dedicado para la métrica (no uses tu cuenta personal ni un admin) y un token:

```sh
# Como admin: crear el usuario y su token (el valor fct_... se muestra una sola vez)
curl -s -X POST http://HUB:8000/api/v1/users -H "Authorization: Bearer $ADMIN" -H 'Content-Type: application/json' \
  -d '{"email":"metrics@hub.local","password":"<contraseña-larga>","role":"viewer"}'
```

Luego, con la sesión de ese usuario, `POST /api/v1/tokens` con `{"name":"prometheus"}`.

Configuración de Prometheus:

```yaml
scrape_configs:
  - job_name: ai-factory
    metrics_path: /metrics
    scrape_interval: 60s
    authorization:
      type: Bearer
      credentials_file: /etc/prometheus/factory-token   # el fct_ del usuario metrics, fuera del repo
    static_configs:
      - targets: ["HUB:8000"]
```

Un token de `viewer` solo sirve para leer: si se filtra, no permite aprobar, reclamar ni administrar. Para quitar el acceso, desactiva el usuario o revoca el token.

### Revisión rápida

```sh
curl -s -H "Authorization: Bearer $METRICS_TOKEN" http://HUB:8000/metrics | grep -E '^factory_(queue_size|claims_active|errors_total)'
```

Alertas sugeridas (ajustar a los umbrales del equipo):
- `factory_queue_size` creciendo sin claims → falta capacidad de devs.
- `increase(factory_errors_total{kind="intake_failed"}[15m]) > 0` → Ollama (`ollama-no-disponible.md`).
- `increase(factory_heartbeat_expiries_total[1h]) > 3` → entornos de devs inestables.
- Ausencia de scrape durante 5 min → la API o la red están caídas.

## Logs

- La API escribe **una línea JSON por evento** en stdout (`LOG_FORMAT=json`, por defecto en compose).
  Docker las guarda con rotación de 10 MB × 5 por servicio.
- Campos del acceso: `ts`, `level`, `logger` (`factory.http`), `msg` (`request`), `method`, `path`,
  `status`, `duration_ms`. La ruta se registra sin query string: no se escriben tokens.
- Los eventos de negocio (cambios de estado, decisiones) van a la base (`work_item_events`), no a los logs:
  ahí está la auditoría.

Consultas habituales:

```sh
docker compose logs -f api                                          # en vivo
docker compose logs --since 1h api | grep '"status": 5'             # errores 5xx de la última hora
docker compose logs --since 1h api | grep '"status": 401' | wc -l   # intentos sin autenticar
```

Si el acceso lo gestiona un proxy delante del hub, sus logs son la fuente para quién entró.

Para leer los logs como JSON en un visor: `docker compose logs api | sed 's/^[^{]*//' | jq .`.

## Retención

- Logs de Docker: rotación por tamaño (ver `despliegue.md`).
- Logs de proceso en la base (`artefactos` de tipo `log` de las etapas del cliente): se borran a los
  `LOG_RETENTION_DAYS` (30 por defecto). Esto no afecta a los eventos de auditoría.
