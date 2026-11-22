#!/usr/bin/env bash
# Siembra el hub local para la demo de memes (ver docs/demo-memes.md).
# Entorno: API (default http://127.0.0.1:8140), ADMIN_EMAIL, ADMIN_PASSWORD, REVIEWER_PASSWORD, DEVELOPER_PASSWORD.
# El token de GitHub sale de `gh auth token` en el momento; no se imprime ni se guarda en disco.
# Idempotente: si el usuario ya existe (409) sigue. Escribe el token de developer en $TOKEN_FILE (fuera del repo).
set -euo pipefail
API="${API:-http://127.0.0.1:8140}"
REPO_GH="${REPO_GH:-maavcrusoe/meme-demo}"
TOKEN_FILE="${TOKEN_FILE:-$HOME/.ai-factory-demo/factory_token.txt}"
: "${ADMIN_EMAIL:?}" "${ADMIN_PASSWORD:?}" "${REVIEWER_PASSWORD:?}" "${DEVELOPER_PASSWORD:?}"

json() { python -c "import json,sys; print(json.load(sys.stdin)$1)"; }
login() { # email password -> access_token
  curl -fsS -X POST "$API/api/v1/auth/login" -H 'Content-Type: application/json' \
    -d "{\"email\":\"$1\",\"password\":\"$2\"}" | json "['access_token']"
}
ADMIN=$(login "$ADMIN_EMAIL" "$ADMIN_PASSWORD")
H=(-H "Authorization: Bearer $ADMIN" -H 'Content-Type: application/json')

mkuser() { # email password role
  code=$(curl -s -o /dev/null -w '%{http_code}' -X POST "$API/api/v1/users" "${H[@]}" \
    -d "{\"email\":\"$1\",\"password\":\"$2\",\"role\":\"$3\"}")
  [ "$code" = 201 ] || [ "$code" = 409 ] || { echo "users $1: HTTP $code" >&2; exit 1; }
}
mkuser reviewer@local.test "$REVIEWER_PASSWORD" reviewer
mkuser developer@local.test "$DEVELOPER_PASSWORD" developer

# Integración GitHub (el proyecto meme-demo lo crea el seed del arranque de la API). Token solo por stdin de curl.
gh auth token | python -c "import json,sys; print(json.dumps({'provider':'github','config':{'repo':'$REPO_GH'},'token':sys.stdin.read().strip()}))" \
  | curl -fsS -X PUT "$API/api/v1/projects/meme-demo/integration" "${H[@]}" -d @- | json "['has_token']"
gh auth token | python -c "import json,sys; print(json.dumps({'token':sys.stdin.read().strip()}))" \
  | curl -fsS -X PUT "$API/api/v1/projects/meme-demo/merge-credential" "${H[@]}" -d @- | json "['has_merge_token']"

# Política: sin humano solo si dificultad low, significado none/minor, planificado y sin rutas sensibles.
# `.factory/*` (un nivel) y no `.factory/**`: el planner mete .factory/specs/<id>/spec.md en cada PR (decisión 016).
curl -fsS -X PUT "$API/api/v1/projects/meme-demo/merge-policy" "${H[@]}" -d '{
  "require_human_always": false,
  "human_if_difficulty": ["medium", "high"],
  "sensitive_paths": ["meme.js", "checks.sh", ".factory/*"],
  "human_if_unplanned": true,
  "human_if_meaning": ["major", "dubious"]
}' | json "['version']"

# Token personal del developer (fct_...). Se muestra una sola vez: va a un fichero fuera del repo.
DEV=$(login developer@local.test "$DEVELOPER_PASSWORD")
mkdir -p "$(dirname "$TOKEN_FILE")"
curl -fsS -X POST "$API/api/v1/tokens" -H "Authorization: Bearer $DEV" -H 'Content-Type: application/json' \
  -d '{"name":"demo-memes"}' | json "['token']" > "$TOKEN_FILE"
chmod 600 "$TOKEN_FILE" 2>/dev/null || true
echo "seed ok. token developer en $TOKEN_FILE"
