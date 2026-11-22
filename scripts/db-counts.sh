#!/usr/bin/env sh
# Huella del estado de la base (conteos por tabla y estados de items). Sirve para comparar antes y después
# de un backup/restore o de un reinicio. Imprime una línea.
set -eu

cd "$(dirname "$0")/.."
docker compose exec -T db sh -c 'psql -X -A -t -U "$POSTGRES_USER" -d "$POSTGRES_DB"' < scripts/db-counts.sql
