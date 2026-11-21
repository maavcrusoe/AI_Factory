# 006: Fase 0, PostgreSQL en Docker y login local

Fecha: 2026-11-21

## Decisiones
- PostgreSQL 16 corre solo en Docker (`docker-compose.yml`, servicio `db`). API y dashboard corren en local. Responde la pregunta abierta de `specs/01`.
- Tests de API contra la base `factory_test` (misma instancia, se crea sola), separada de la de desarrollo.
- Admin sembrado desde `.env` (`ADMIN_EMAIL`, `ADMIN_PASSWORD`) al arrancar la API. Crea o actualiza el usuario; el `.env` manda.
- Hash de contraseñas con `hashlib.scrypt` de la librería estándar (sin dependencia nueva).
- Login: `POST /api/v1/auth/login` devuelve token firmado HMAC (`APP_SECRET_KEY`, TTL 8 h). `GET /api/v1/auth/me` valida el token. El dashboard guarda el token en cookie httpOnly desde una server action.
- Dashboard con Next.js 16 y `cacheComponents`. Las páginas dinámicas usan `export const instant = false`.
- Gestor de Python: uv. Scripts de raíz compatibles con cmd.exe.

## Pendiente
- Sin `npm test` en el dashboard: no hay runner de UI aprobado (nueva dependencia, pedir antes).
