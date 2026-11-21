# 008: Fase 2, adapters de repo/tracker (2026-11-21)

## Decisiones
- **Interfaces**: `TrackerAdapter` (`fetch_new_items`, `get_item`, `comment`, `set_labels`) y `RepoAdapter` (`create_branch`, `open_pr`, `merge_pr`, `get_diff`) en `app/adapters/base.py`. Registro único `ADAPTERS` en `app/adapters/__init__.py`. Añadir un proveedor = una clase más una línea en ese registro; sin tocar dominio.
- **GenericAdapter**: entrada por webhook firmado (ya existente). Sin remoto: sondeo vacío y operaciones de remoto no soportadas.
- **GitHubAdapter**: token por `Bearer`, API REST. Sondeo de issues con la etiqueta de fábrica (`label`, por defecto `factory`). Descarta entradas con `pull_request`. Una página de 100 por sondeo (ceiling conocido).
- **AzureDevOpsAdapter**: REST con PAT en Basic (`":" + PAT`). Ingesta por WIQL sobre la etiqueta (tags). Etiquetas por `System.Tags` separadas por `;`. PATCH con `application/json-patch+json`. **Sin pruebas reales**: el owner indicó que aún no hay organización ni proyecto. Solo mocks REST. Las versiones de API (`7.1`, comentarios `7.0-preview.3`) no están verificadas contra una org real. `get_diff` no está implementado (pendiente).
- **Sondeo**: GitHub cada 60 s, Azure DevOps cada 300 s (5 min). Configurable por proyecto con `pollSeconds` (mínimo 15). Hilo de fondo en el arranque de la API, desactivable con `TRACKER_POLLING_ENABLED=false` (los tests lo desactivan). Un fallo de un tracker se registra por tipo de error y no para el bucle. Ceiling: un solo proceso de API; con varios habría que bloquear.
- **Ingesta idempotente**: `idempotency_key = "<provider>:<remote_id>"`. Se reutiliza la restricción única de Fase 1. El item y su enlace (`tracker_links`) se crean en la misma transacción; en una carrera se revierten los dos. El intake corre en un hilo propio. `services/ingest.py` es el alta compartida por la API y el sondeo.
- **Etiquetas, el hub gana**: las gestionadas son la etiqueta de fábrica y `taken by <usuario>`. El resto de etiquetas del remoto se respetan. El hub escribe el conjunto completo gestionado (`desired`) y reemplaza solo lo gestionado.
- **Marcador de origen**: `tracker_links.managed_labels` guarda lo último que escribió el hub. Si el hub cambia algo, el evento es `labels_pushed`; si el remoto cambió a mano, `label_reverted`, con actor `hub-sync`. Sin cambios no se escribe nada ni se genera evento, así no hay bucles ni ruido en SSE.
- **Comentarios del hub**: llevan el marcador oculto `<!-- factory:origin=hub -->`. El helper existe; aún no lo usa ningún flujo (lo necesitará el claim de Fase 3).
- **Tokens**: cifrados con Fernet (`cryptography`), clave en `TOKEN_ENCRYPTION_KEY`, separada de `APP_SECRET_KEY`. Sin clave, guardar un token devuelve 503 y no se guarda nada. La API solo devuelve `has_token`, nunca el token ni un fragmento. El token no va en `config` (422). Solo admin puede escribirlo (`PUT /api/v1/projects/{slug}/integration`).
- **Migración**: `0003_integraciones_tracker` (tablas `project_integrations` y `tracker_links`).
- **Pruebas reales**: `GITHUB_REAL=1 pytest -m github_real` contra `maavcrusoe/meme-demo`. El token sale de `gh auth token` en memoria, nunca se guarda. Crea un issue temporal y lo cierra al terminar; borra la etiqueta de prueba. La lista de GitHub tarda unos 6 s en reflejar un issue nuevo, y el test espera con plazo.
- **Fuera de este PR**: UI en el dashboard (no necesaria para esta fase), claim y `taken by` desde la API (Fase 3), `get_diff` y el resto de operaciones de repo en Azure DevOps.

## Verificación
- `pytest`: 52 pasan, 1 se salta (Ollama real). `GITHUB_REAL=1 pytest -m github_real`: pasa.
- Migración `0003`: upgrade, downgrade, upgrade y `alembic check` sin diferencias.
- Sin Playwright: no hay cambios de UI.

## Pendiente
- Azure DevOps: probar con organización real, verificar versiones de API y decidir `get_diff`.
- Claim y `taken by` desde la API (Fase 3).
- Varios procesos de API: bloqueo del sondeo.
