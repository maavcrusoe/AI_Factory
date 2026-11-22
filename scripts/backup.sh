#!/usr/bin/env sh
# Copia de seguridad de PostgreSQL (pg_dump formato custom) en backups/, verificada con pg_restore -l.
# Uso: scripts/backup.sh            (la base debe estar levantada con docker compose)
# Variables: BACKUP_DIR (por defecto backups/), COMPOSE_PROJECT_NAME si usas otro proyecto compose.
set -eu

cd "$(dirname "$0")/.."
BACKUP_DIR="${BACKUP_DIR:-backups}"
mkdir -p "$BACKUP_DIR"

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT="$BACKUP_DIR/factory-$STAMP.dump"

# Las credenciales viven en el contenedor (variables de compose): no pasan por el host.
docker compose exec -T db sh -c 'pg_dump -Fc --no-owner -U "$POSTGRES_USER" -d "$POSTGRES_DB"' > "$OUT.tmp"

# Un dump vacío o truncado no se da por bueno: pg_restore -l debe poder leer su índice.
docker compose exec -T db pg_restore -l < "$OUT.tmp" > /dev/null
mv "$OUT.tmp" "$OUT"

echo "Copia creada y verificada: $OUT ($(wc -c < "$OUT") bytes)"
