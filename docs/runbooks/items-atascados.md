# Items atascados

Un item "atascado" es uno que lleva demasiado tiempo en un estado sin que nadie lo mueva. Mira primero
el dashboard (`/board` filtrado por estado, y la línea de tiempo del detalle) y los eventos del item.
Cada transición deja un evento de auditoría con su `kind`.

## Tabla de estados y qué esperar

| Estado | Qué significa | ¿Se mueve solo? | Qué hacer si lleva mucho |
|---|---|---|---|
| `RECEIVED`, `NORMALIZING`, `TRIAGE` | Intake en curso | No, salvo al reiniciar | Tras un reinicio, la API pasa a `WAITING_HUMAN_TRIAGE` (evento `startup_sweep`). Si sigue ahí sin reinicio, mirar logs de `factory.http` y `docs/runbooks/ollama-no-disponible.md` |
| `WAITING_HUMAN_TRIAGE` | El intake falló o no decidió (`intake_failed`, plazo de 60 s) | No | Decidir en `/inbox`: aceptar o rechazar. Nunca se acepta sin humano |
| `QUEUED` | Esperando a un dev con `/factory` | No | Si nadie lo coge, es falta de capacidad, no un fallo: revisar la cola del proyecto |
| `CLAIMED` | Un dev lo tiene | Sí: sin latido 30 min vuelve a `QUEUED` (evento `heartbeat_expired`) | Ver "Claim colgado" |
| `PR_OPEN`, `FIXING`, `WAITING_HUMAN_MERGE`, `READY_TO_MERGE` | Pipeline y revisión | No | Decisión humana en `/approvals`; ver política del proyecto |
| `MERGING` | Merge en curso | No | Ver "Merge colgado" |

## Claim colgado (`CLAIMED` sin latido)

1. Mira `last_heartbeat_at` en el detalle del item. Si son más de 30 min, el job de caducidad lo
   devuelve a `QUEUED` solo (tick en segundo plano de la API). Espera un ciclo.
2. Si el dev sigue trabajando pero no llega el latido (su máquina, red o token), habla con él. No hay
   que tocar la base: si libera el claim con `/factory` o desde el dashboard, el item vuelve a `QUEUED`.
3. Si el dev no responde y necesitas el item ya: el claim caduca solo. No hace falta forzarlo.
4. Comprueba la caducidad en las métricas: `factory_heartbeat_expiries_total` sube por proyecto.
   Muchas caducidades seguidas del mismo dev → problema de su entorno, no del hub.

Los 409 `ya cogido por X` son correctos: el claim es exclusivo.

## Intake atascado (`RECEIVED`/`TRIAGE` tras un rato)

- Revisa si la API se reinició: `docker compose logs api | grep "Barrido al arrancar"` (warning en logs) o el
  evento `startup_sweep` en la línea de tiempo del item.
- Si no hubo reinicio, el plazo total del intake (`INTAKE_DEADLINE_SECONDS`, 60 s) debería haberlo
  pasado a `WAITING_HUMAN_TRIAGE`. Si no lo hizo, revisa `docker compose logs api` por errores y
  reinicia la API (`docker compose restart api`): el barrido de arranque lo pasa a revisión humana.

## Merge colgado (`MERGING`)

El merge escribe `merge_started` antes de llamar al proveedor. Si el proceso muere entre medias, el
item queda en `MERGING`. **No hay recuperación automática para este estado** (el barrido de arranque solo
cubre `RECEIVED`, `NORMALIZING` y `TRIAGE`). Procedimiento:

1. Mira el PR en GitHub/Azure DevOps y anota su estado real (abierto, fusionado o cerrado).
2. Si el PR está fusionado: el item debe quedar en `MERGED`. Si el PR sigue abierto: el item debe volver
   a `READY_TO_MERGE` y el merge se repite desde `/approvals` con el SHA del gate.
3. Un cambio manual de estado en la base no deja el evento de auditoría adecuado. Antes de tocar la base,
   abre un issue con el id del item, el estado del PR y la salida de `docker compose logs api` del momento.

Queda como punto abierto: añadir una transición de recuperación para `MERGING` (ver PR de Fase 7).

## Errores de merge repetidos

`merge_failed` vuelve el item a `READY_TO_MERGE` con el motivo en el evento. Revisa el motivo:
- credencial de merge caducada → rotar según `rotacion-tokens.md` (secreto C),
- rama protegida o checks pendientes en el proveedor → resolver en el proveedor y reintentar desde `/approvals`,
- SHA distinto del gate → el dev debe volver a ejecutar el gate final.

## Consultas útiles (solo lectura)

```sh
docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "select status, count(*) from work_items group by status order by 1"'
docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "select kind, to_status, actor, created_at from work_item_events where work_item_id = <ID> order by id"'
```
