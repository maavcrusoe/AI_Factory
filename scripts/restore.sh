#!/usr/bin/env sh
# Restaura una copia de backup.sh. DESTRUCTIVO: sustituye la base actual.
# Uso: CONFIRM=si scripts/restore.sh backups/factory-AAAAMMDDTHHMMSSZ.dump
# Pasos: para API y dashboard -> recrea la base -> pg_restore -> migraciones (por si el dump es antiguo) -> arranca.
set -eu

cd "$(dirname "$0")/.."
FILE="${1:?uso: CONFIRM=si scripts/restore.sh <fichero.dump>}"

[ -f "$FILE" ] || { echo "No existe: $FILE" >&2; exit 1; }
[ "${CONFIRM:-}" = "si" ] || { echo "Esto borra la base actual. Repite con CONFIRM=si." >&2; exit 1; }

docker compose stop api dashboard
docker compose exec -T db sh -c 'dropdb --if-exists -U "$POSTGRES_USER" "$POSTGRES_DB" && createdb -U "$POSTGRES_USER" "$POSTGRES_DB"'
docker compose exec -T db sh -c 'pg_restore --no-owner --exit-on-error -U "$POSTGRES_USER" -d "$POSTGRES_DB"' < "$FILE"
docker compose run --rm migrate
docker compose up -d api dashboard

echo "Restaurado desde $FILE. Comprueba con scripts/db-counts.sh y /health."
