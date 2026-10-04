#!/usr/bin/env bash
#
# Back up the live database into backups/, and prove the file reads back.
#
# Usage:  ./scripts/backup.sh
#
# The path of the file it wrote is the only thing printed to stdout, so a caller
# can capture it; progress goes to stderr.
#
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

readonly DB_SERVICE="db"
readonly DB_USER="finance"
readonly DB_NAME="finance"
readonly BACKUP_DIR="backups"

if ! command -v docker >/dev/null 2>&1; then
  echo "docker is required to run this." >&2
  exit 1
fi

if ! docker compose ps --services --status running 2>/dev/null | grep -qx "$DB_SERVICE"; then
  echo "The '$DB_SERVICE' service is not running. Start it with: docker compose up -d" >&2
  exit 1
fi

mkdir -p "$BACKUP_DIR"
# Seconds in the name, so two backups in the same minute cannot collide.
target="$BACKUP_DIR/finance-$(date +%Y-%m-%d-%H%M%S).dump"

# Never overwrite: a silent replacement would lose the earlier backup.
if [ -e "$target" ]; then
  echo "Refusing to overwrite $target" >&2
  exit 1
fi

echo "Dumping '$DB_NAME' into $target ..." >&2
docker compose exec -T "$DB_SERVICE" pg_dump \
  --username="$DB_USER" --dbname="$DB_NAME" --format=custom >"$target"

# A dump is not a backup until it reads back: pg_restore lists the file's table
# of contents, so a truncated or empty file fails here rather than at the moment
# everything depends on it.
tables="$(docker compose exec -T "$DB_SERVICE" pg_restore --list <"$target" | grep -c 'TABLE DATA' || true)"

if [ "$tables" -eq 0 ]; then
  echo "That dump holds no table data, so it is not a backup. Removing it." >&2
  rm -f "$target"
  exit 1
fi

size="$(stat -c '%s' "$target")"
echo "Verified: $tables tables with data, $size bytes." >&2
echo "Keep a copy of it somewhere other than this machine." >&2

echo "$target"
