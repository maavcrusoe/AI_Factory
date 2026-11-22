# Backup, restore y prueba de reinicio

Qué se copia: la base PostgreSQL completa (proyectos, usuarios, tokens hasheados, items, eventos,
artefactos, políticas e integraciones con tokens **cifrados**). No se copia `.env`: guárdalo aparte, en
un gestor de secretos, porque sin `TOKEN_ENCRYPTION_KEY` los tokens cifrados no se pueden leer.

Formato: `pg_dump -Fc` (custom). Cada copia se verifica con `pg_restore -l` antes de darla por buena.

## Copia de seguridad

```sh
scripts/backup.sh
# Copia creada y verificada: backups/factory-AAAAMMDDTHHMMSSZ.dump (...)
```

- Se guarda en `backups/` (ignorado por git). Copia fuera del servidor cada día.
- Programación diaria (cron del servidor, como el usuario que ejecuta Docker):
  ```cron
  30 2 * * * cd /ruta/ai-factory && scripts/backup.sh >> /var/log/factory-backup.log 2>&1
  ```
- Retención: borrar copias de más de 14 días (ajustar a la política del equipo):
  ```sh
  find backups -name 'factory-*.dump' -mtime +14 -delete
  ```
- Comprobar que la copia sirve: al menos una vez al mes, restaurar en un proyecto compose de prueba
  (ver "Prueba de restauración").

## Restore

**Destructivo**: sustituye la base actual. Pide confirmación explícita con `CONFIRM=si`.

```sh
CONFIRM=si scripts/restore.sh backups/factory-AAAAMMDDTHHMMSSZ.dump
```

Lo que hace, en orden: para `api` y `dashboard`, recrea la base, ejecuta `pg_restore --exit-on-error`,
corre `migrate` (por si la copia es de una versión anterior del esquema) y vuelve a arrancar la API y el
dashboard. Después:

```sh
scripts/db-counts.sh      # huella del estado: comparar con la anotada antes del incidente
curl -fsS http://127.0.0.1:8000/health
```

Nota: al arrancar, la API pasa a revisión humana los items que quedaron en `RECEIVED`, `NORMALIZING` o
`TRIAGE` (barrido de arranque, intencionado). Si la copia contenía items en esos estados, verás eventos
`startup_sweep` tras el restore. No es pérdida de datos.

## Prueba de restauración (cómo se verificó)

Se probó en un proyecto compose aislado (`COMPOSE_PROJECT_NAME=factory-ops-test`), con datos creados por la API:

| Paso | Resultado |
|---|---|
| Huella antes de la copia | `projects=1 users=2 tokens=1 items=1 events=3 states=TRIAGE:1` |
| `scripts/backup.sh` | Copia de 32 858 bytes creada y verificada |
| `DROP DATABASE` con API parada | Base eliminada (`database "factory" does not exist`) |
| `CONFIRM=si scripts/restore.sh` | Restaurado, migración OK, API `healthy` |
| Huella después del restore | `projects=1 users=2 tokens=1 items=1 events=4 states=WAITING_HUMAN_TRIAGE:1` |

Las diferencias son las esperadas: el item en `TRIAGE` pasó a `WAITING_HUMAN_TRIAGE` por el barrido de
arranque (+1 evento `startup_sweep`). Proyectos, usuarios, tokens e items se conservan.

## Prueba de reinicio

```sh
scripts/restart-test.sh
# Antes:   projects=1 users=2 tokens=1 items=1 events=4 states=WAITING_HUMAN_TRIAGE:1
# Después: projects=1 users=2 tokens=1 items=1 events=4 states=WAITING_HUMAN_TRIAGE:1
# OK: el reinicio no pierde estado.
```

Reinicia `db`, `api` y `dashboard`, espera a `/health` y compara la huella. Sale con código 1 si cambia.
Ejecutar tras cada despliegue o antes de tocar la base.

## Limpieza de la prueba

Si restauras en un proyecto de prueba, bórralo al terminar con `docker compose -p <proyecto> down -v`.
La opción `-v` borra volúmenes: úsala solo en el proyecto de prueba, nunca en el del servidor.
