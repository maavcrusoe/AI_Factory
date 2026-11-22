# 013: Fase 7, operación

Fecha: 2026-11-22. Rama `factory/fase-7`.

## Decisiones

1. **Compose con cuatro servicios**: `db` (postgres:16), `migrate` (paso único `alembic upgrade head`),
   `api` y `dashboard`. `api` depende de `migrate` con `service_completed_successfully`: si las migraciones
   fallan, la API no arranca.
2. **Red**: `backend` interna (`internal: true`) para `db`, `migrate`, `api` y `dashboard`. `edge` da salida a
   la red a `api` (Ollama, GitHub, Azure DevOps) y es la única forma de publicar puertos. `db` y `migrate`
   no tienen puertos publicados. Para desarrollo local, `docker-compose.dev.yml` publica `db` en loopback.
3. **Publicación por defecto en loopback**: `API_BIND` y `DASHBOARD_BIND` valen `127.0.0.1`. El servidor
   cambia la IP en `.env`. Así un despliegue nuevo no queda expuesto por accidente.
4. **Secretos obligatorios**: `APP_SECRET_KEY`, `TOKEN_ENCRYPTION_KEY`, `POSTGRES_*` usan `${VAR:?...}`:
   compose no arranca si faltan. `.env` se pasa con `env_file` y no entra en la imagen (`.dockerignore`).
5. **Una imagen para la API y las migraciones**, con `uvicorn --workers 1`: el sondeo, la caducidad y la
   retención son hilos del proceso y se ejecutarían una vez por worker.
6. **Dashboard en modo standalone** (`output: "standalone"`), Node 22 Alpine, usuario no root.
7. **Métricas en `/metrics` calculadas desde PostgreSQL**, solo admin. Así sobreviven a reinicios y no
   hace falta estado en memoria. Se eligió el rol admin por simplicidad; un rol de solo lectura para
   métricas queda pendiente.
8. **Logs JSON** por línea, con un middleware de acceso (`factory.http`) que no registra query strings.
   `uvicorn --no-access-log` evita la línea duplicada en texto plano.
9. **Rotación de la clave de cifrado sin pérdida**: `TOKEN_ENCRYPTION_KEY` admite varias claves separadas
   por coma (`MultiFernet`). La primera cifra, todas descifran. El comando `python -m app.ops
   rotate-token-key` re-cifra todos los tokens de integración en una transacción.
10. **Backups con `pg_dump -Fc`** y verificación con `pg_restore -l` antes de dar la copia por buena.
    `restore.sh` exige `CONFIRM=si` y ejecuta migraciones tras el restore.
11. **Dev tokens e integración**: procedimiento documentado sobre endpoints existentes (no se añade
    endpoint nuevo). Un token comprometido se combate desactivando el usuario (`is_active`), porque la
    autenticación por token exige usuario activo.
12. **CI mínima** en GitHub Actions: pytest con Postgres 16 como servicio, y `npm run lint` + `tsc --noEmit`
    del dashboard.

## Lo que no se decide aquí

- Servidor y sistema operativo de despliegue: pendiente. La configuración es genérica (Linux + Docker Compose v2.24+).
- Recuperación automática de items en `MERGING` tras un fallo a medio merge: pendiente.
- Rol de solo lectura para métricas: pendiente.
- Copias de seguridad fuera del servidor: el procedimiento está documentado, el destino lo decide el equipo.

## Verificación

- `pytest`: 115 pasan, 2 saltados (marcadores de Ollama y GitHub reales).
- Imágenes construidas; stack levantado en un proyecto compose de prueba.
- Backup, `DROP DATABASE`, restore: huella íntegra salvo el barrido de arranque previsto.
- Prueba de reinicio: huella idéntica.
- Rotación de `TOKEN_ENCRYPTION_KEY`: re-cifrado OK; con la clave antigua sola, falla.
- `/metrics`: 401 anónimo, 403 developer, 200 admin.
