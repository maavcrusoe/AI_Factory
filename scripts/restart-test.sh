#!/usr/bin/env sh
# Prueba de reinicio: reinicia base, API y dashboard, espera a /health y compara la huella del estado.
# Debe dar exactamente la misma huella (scripts/db-counts.sh). Si cambia, falla con código 1.
# Nota: al arrancar, la API pasa a revisión humana los items que quedaron en RECEIVED/NORMALIZING/TRIAGE
# (barrido de arranque, intencionado). Esta prueba no crea items en esos estados.
set -eu

cd "$(dirname "$0")/.."
API_PORT="${API_PORT:-8000}"

before="$(scripts/db-counts.sh)"
echo "Antes:   $before"

docker compose restart db api dashboard

i=0
until curl -fsS "http://127.0.0.1:$API_PORT/health" > /dev/null 2>&1; do
  i=$((i + 1))
  [ "$i" -lt 60 ] || { echo "La API no responde tras reiniciar" >&2; exit 1; }
  sleep 2
done

after="$(scripts/db-counts.sh)"
echo "Después: $after"

if [ "$before" = "$after" ]; then
  echo "OK: el reinicio no pierde estado."
else
  echo "FALLO: el estado cambió tras el reinicio." >&2
  exit 1
fi
