# Demo de memes: estados visibles en el dashboard

Hub local con `meme-demo` y dos peticiones de ejemplo: una pasa **sin humano** y termina `MERGED`; otra espera **aprobación humana**.
Estado de referencia (2026-11-22): items #7 (auto, PR #8 mergeado), #3 (humano, PR #9 en borrador) y #1 (humano por tocar `checks.sh`, PR #7 en borrador).

## Puertos y secretos
Usa puertos libres. Aquí: Postgres 5440, API 8140, dashboard 3140. `.env` (no se commitea) lleva `POSTGRES_PORT`, `API_PORT`, `DASHBOARD_PORT`, `DATABASE_URL`, `APP_SECRET_KEY`, `ADMIN_*`, `TOKEN_ENCRYPTION_KEY`. Ollama lento: `INTAKE_DEADLINE_SECONDS=240` y `OLLAMA_TIMEOUT_SECONDS=230`.
Contraseñas y token de developer: `~/.ai-factory-demo/` (`credentials.txt`, `factory_token.txt`). Fuera del repo.

## Levantar
```sh
POSTGRES_PORT=5440 docker compose -p ai-factory -f docker-compose.yml -f docker-compose.dev.yml up -d db
(cd apps/api && uv sync && uv run alembic upgrade head)
(cd apps/api && uv run uvicorn app.main:app --host 127.0.0.1 --port 8140) &
(cd apps/dashboard && npm ci && API_URL=http://127.0.0.1:8140 npx next build && API_URL=http://127.0.0.1:8140 npx next start -H 127.0.0.1 -p 3140) &
```
Usa `127.0.0.1`, no `localhost` (en Windows tarda 15 s por `::1`).

## Sembrar
Usuarios `reviewer@local.test` y `developer@local.test`, integración GitHub y credencial de merge (ambas con `gh auth token`, cifradas en BD), política v1 y token personal:
```sh
set -a; . ./.env; set +a
REVIEWER_PASSWORD=... DEVELOPER_PASSWORD=... scripts/demo-memes-seed.sh
```
Política v1 de `meme-demo`: `require_human_always:false`, `human_if_difficulty:[medium,high]`, `sensitive_paths:[meme.js, checks.sh, .factory/*]`, `human_if_unplanned:true`, `human_if_meaning:[major,dubious]`. El resto de proyectos siguen en la política global: todo humano.

## Peticiones
Como `developer`, `POST /api/v1/inputs` con `source:"form"` y `X-Idempotency-Key` (una por petición):
- **A (automática)**: "Cambiar el título de la página a Generador de memes". Solo `index.html`; pide no tocar `checks.sh`.
- **B (humana)**: "Añadir selector de plantilla y generador de chistes". Toca `meme.js` (`drawMeme`): ruta sensible.

Espera a `QUEUED` (intake, hasta ~2 min con Ollama cargado) y ejecuta el cliente, uno tras otro (A antes que B):
```sh
export FACTORY_TOKEN="$(cat ~/.ai-factory-demo/factory_token.txt)" FACTORY_HUB_URL=http://127.0.0.1:8140
python .claude/skills/factory/scripts/pipeline.py --repo <clon>/meme-demo --item <id>
```
`FACTORY_HUB_URL` evita tocar `.factory/config.yaml` de meme-demo (que apunta a 8000).

## Qué ver
- `/board`: A en "Mergeada", B (y #1) en "Aprobación humana".
- `/work/<id>`: línea de tiempo (`gate_reported`, `policy_evaluated`, `merge_started`, `merged` en A), logs.
- `/approvals/3` (reviewer o admin): gate, "ruta sensible: meme.js", diff, botones. **No se aprobó**: lo decide el dueño.

## Parar
```sh
docker compose -p ai-factory down            # sin -v: conserva los datos
# API y dashboard: matar por puerto
powershell -c "Get-NetTCPConnection -LocalPort 8140,3140 -State Listen | % { Stop-Process -Id \$_.OwningProcess -Force }"
```
