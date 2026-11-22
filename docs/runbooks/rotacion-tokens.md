# Rotación de tokens y secretos

Hay cinco tipos de secreto. Rotar uno no obliga a rotar los demás.

| Secreto | Dónde vive | Efecto de rotarlo |
|---|---|---|
| A. Token de desarrollador `fct_...` | Variable `FACTORY_TOKEN` del dev; hash SHA-256 en la base | Solo afecta al dev que lo usa |
| B. Token de integración (tracker/repo) | Cifrado en `project_integrations.token_encrypted` | Cambia el acceso del hub a GitHub/Azure DevOps |
| C. Credencial de merge | Cifrada en `merge_token_encrypted` | Cambia quién puede hacer merge |
| D. `TOKEN_ENCRYPTION_KEY` | `.env` del servidor | Hay que re-cifrar B y C (procedimiento abajo) |
| E. `APP_SECRET_KEY` y `ADMIN_PASSWORD` | `.env` del servidor | Cierra todas las sesiones del dashboard |

## A. Tokens de desarrollador

Rotación normal (un dev, cada 90 días o al cambiar de equipo):

1. Crear el token nuevo con la sesión del dev (se muestra una sola vez):
   ```sh
   TOKEN=$(curl -s -X POST http://HUB:8000/api/v1/auth/login -H 'Content-Type: application/json' \
     -d '{"email":"<email>","password":"<password>"}' | sed -n 's/.*"access_token":"\([^"]*\)".*/\1/p')
   curl -s -X POST http://HUB:8000/api/v1/tokens -H "Authorization: Bearer $TOKEN" \
     -H 'Content-Type: application/json' -d '{"name":"portatil-2026-11"}'
   ```
2. Guardar el `token` en `FACTORY_TOKEN` del perfil del dev y comprobar con `/factory`.
3. Revocar el anterior (el dev puede hacerlo con su sesión):
   ```sh
   curl -s http://HUB:8000/api/v1/tokens -H "Authorization: Bearer $TOKEN"        # lista con id
   curl -s -X DELETE http://HUB:8000/api/v1/tokens/<id> -H "Authorization: Bearer $TOKEN"
   ```

Token comprometido o dev que se va:

- Desactivar el usuario de inmediato: un admin hace `PATCH /api/v1/users/<id>` con `{"is_active": false}`.
  Un usuario inactivo no autentica con ningún token. Después, revocar los tokens y reactivar solo si procede.
- Un admin no puede listar ni revocar tokens ajenos desde la API: los tokens solo se gestionan desde la
  sesión de su dueño. Por eso la desactivación es el primer paso.

## B y C. Tokens de integración y credencial de merge

Se cambian por API. El valor se envía una vez y no se devuelve (`GET` solo indica si hay token).

```sh
# Token del tracker/repo (lectura y etiquetas)
curl -s -X PUT http://HUB:8000/api/v1/projects/<slug>/integration \
  -H "Authorization: Bearer $ADMIN" -H 'Content-Type: application/json' \
  -d '{"provider":"github","config":{"repo":"owner/repo"},"token":"<NUEVO_TOKEN>"}'

# Credencial de merge (solo la usa el controlador de merge)
curl -s -X PUT http://HUB:8000/api/v1/projects/<slug>/merge-credential \
  -H "Authorization: Bearer $ADMIN" -H 'Content-Type: application/json' -d '{"token":"<NUEVO_TOKEN>"}'

# Comprobar: has_token y has_merge_token deben ser true
curl -s http://HUB:8000/api/v1/projects/<slug>/integration -H "Authorization: Bearer $ADMIN"
```

El PUT de integración sustituye `provider` y `config` completos: si omites `config`, queda vacío. Manda
siempre los dos. Sin `token`, se conserva el guardado. Si cambias de repo con items enlazados, la API
responde 409 (protección de etiquetas en issues ajenos).

Orden recomendado: crear el token nuevo en el proveedor (GitHub/Azure DevOps) → PUT → comprobar con una
sincronización o con `/inputs` → revocar el token antiguo en el proveedor.

## D. Rotar `TOKEN_ENCRYPTION_KEY` sin perder tokens

`TOKEN_ENCRYPTION_KEY` admite varias claves separadas por coma: la primera cifra y todas descifran.
Procedimiento probado en un proyecto compose de prueba (rotación con API activa, sin pérdida):

1. Generar la clave nueva:
   ```sh
   python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```
2. Poner en `.env` la clave nueva **primero** y la antigua después: `TOKEN_ENCRYPTION_KEY=NUEVA,ANTIGUA`.
   Recrear la API: `docker compose up -d api`.
3. Re-cifrar todos los tokens con la clave primaria:
   ```sh
   docker compose run --rm --no-deps api python -m app.ops rotate-token-key
   # Tokens re-cifrados: N
   ```
   Es todo o nada: si un token no descifra con ninguna clave, el comando falla y no cambia nada.
4. Quitar la clave antigua: `.env` con `TOKEN_ENCRYPTION_KEY=NUEVA` y `docker compose up -d api`.
5. Comprobar: `docker compose run --rm --no-deps api python -m app.ops rotate-token-key` debe imprimir el
   número de tokens sin error. Con la clave antigua sola debe fallar con `TokenCryptoError`.

Guardar la clave antigua fuera del servidor hasta comprobar el paso 5 y la siguiente copia de seguridad.
Una copia de seguridad sin su `TOKEN_ENCRYPTION_KEY` no sirve para recuperar tokens.

## E. `APP_SECRET_KEY` y `ADMIN_PASSWORD`

- `APP_SECRET_KEY`: cambiarla invalida todas las sesiones del dashboard (cookies firmadas). Los tokens
  `fct_` no cambian. Recrear con `docker compose up -d api` y avisar al equipo de que vuelva a entrar.
- `ADMIN_PASSWORD`: la API guarda el admin desde `.env` **al arrancar**. Cambiar el valor y recrear
  `docker compose up -d api` lo aplica. Usa una contraseña nueva de ≥ 20 caracteres.
