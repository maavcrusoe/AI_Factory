# Despliegue del hub

Objetivo: levantar el hub completo (PostgreSQL 16, migraciones, API y dashboard) con un solo comando.
Servidor: Linux genérico con Docker Engine y el plugin Compose v2.24 o posterior. Sin Kubernetes.

## Requisitos

- Docker Engine y `docker compose version` ≥ 2.24.
- `git`, y acceso de salida desde el servidor a Ollama (`OLLAMA_URL`), GitHub y Azure DevOps si se usan.
- Puertos libres en el host: API (`API_PORT`, 8000 por defecto) y dashboard (`DASHBOARD_PORT`, 3000).

## Primera instalación

1. Clonar el repo y entrar en la carpeta:
   ```sh
   git clone <url-del-repo> ai-factory && cd ai-factory
   ```
2. Crear `.env` a partir de la plantilla. **No se commitea.**
   ```sh
   cp .env.example .env
   ```
3. Rellenar los secretos. Cada valor se genera una vez:
   ```sh
   python3 -c "import secrets; print(secrets.token_urlsafe(48))"                                  # APP_SECRET_KEY
   python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"     # TOKEN_ENCRYPTION_KEY
   ```
   Ajustar también `POSTGRES_PASSWORD` (solo letras y números: se inserta sin codificar en la URL),
   `ADMIN_EMAIL`, `ADMIN_PASSWORD`, `OLLAMA_URL` y `LOG_FORMAT=json`.
4. Exposición en la red. Por defecto la API y el dashboard solo escuchan en `127.0.0.1`.
   Para que el equipo llegue desde la LAN, poner en `.env` la IP del servidor o `0.0.0.0`:
   ```sh
   API_BIND=0.0.0.0
   DASHBOARD_BIND=0.0.0.0
   ```
   La base de datos y las migraciones no tienen puerto publicado: solo las ve la red interna `backend`.
5. Levantar:
   ```sh
   docker compose up -d --build
   ```
   Orden de arranque: `db` (healthcheck `pg_isready`) → `migrate` (`alembic upgrade head`, termina con
   código 0) → `api` (healthcheck `/health`) → `dashboard`. Si `migrate` falla, la API no arranca:
   revisar con `docker compose logs migrate`.
6. Comprobar:
   ```sh
   docker compose ps                       # todos "healthy" o "running"; migrate en "exited (0)"
   curl -fsS http://127.0.0.1:8000/health  # {"status":"ok","database":"ok"}
   ```
   Entrar en el dashboard con `ADMIN_EMAIL` y `ADMIN_PASSWORD`.

Si el puerto está ocupado, cambiar `API_PORT`/`DASHBOARD_PORT` en `.env`. Las variables del shell
tienen prioridad sobre `.env`, así que pueden usarse para una prueba puntual.

## Actualizar

Antes de cada actualización, hacer una copia de seguridad (ver `backup-restore.md`).

```sh
scripts/backup.sh
git pull
docker compose up -d --build
docker compose logs --tail 50 migrate  # debe terminar sin error
```

`migrate` se ejecuta en cada despliegue y es idempotente. Las migraciones son hacia delante: volver a
una versión anterior del código no deshace el esquema. Para volver atrás, restaura la copia tomada antes
de actualizar (ver `backup-restore.md`).

## Operación diaria

- Ver logs: `docker compose logs -f api` (una línea JSON por evento, ver `metricas-y-logs.md`).
- Reinicio de un servicio: `docker compose restart api`. Los datos están en el volumen `pgdata`; un
  reinicio no los pierde (prueba en `backup-restore.md`).
- Parar sin perder datos: `docker compose down`. **No usar `down -v`**: borra el volumen con la base.
- Arranque automático: los servicios tienen `restart: unless-stopped`; Docker los levanta tras un reinicio
  del servidor si el servicio Docker está habilitado (`systemctl enable docker`).

## Red y seguridad

- `backend` es interna: `db` y `migrate` no salen a Internet y no tienen puertos publicados.
- `edge` da salida a la red a la API (Ollama, GitHub, Azure DevOps) y publica API y dashboard.
- El `.env` se pasa a los contenedores por `env_file`. La imagen no lo incluye (ver `.dockerignore`).
- Los logs de Docker rotan a 10 MB × 5 ficheros por servicio.

## Desarrollo local (no es el servidor)

`docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d db` publica PostgreSQL solo en
`127.0.0.1:${POSTGRES_PORT}` para que `npm run dev` (API y dashboard en el host) lo use.

## Problemas frecuentes

| Síntoma | Causa probable | Qué hacer |
|---|---|---|
| `required variable APP_SECRET_KEY is missing` | Falta una variable obligatoria en `.env` | Completar `.env` (ver paso 3) |
| `migrate` sale con error | Base no lista, contraseña con caracteres especiales o migración rota | `docker compose logs migrate`; si la URL tiene símbolos, cambiar `POSTGRES_PASSWORD` antes del primer arranque |
| `ports are not available` / `bind: ... only one usage` | Puerto ocupado en el host | Cambiar `API_PORT` o `DASHBOARD_PORT` |
| API `503` en `/health` | Base de datos no accesible | `docker compose ps db`; `docker compose logs db` |
| Login del dashboard falla tras cambiar `.env` | La API guarda el admin al arrancar | `docker compose up -d api` para que relea `.env` |
