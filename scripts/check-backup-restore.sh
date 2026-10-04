#!/usr/bin/env bash
#
# Prove a backup really restores: take one, restore it into a scratch database,
# and compare every table's row count between the live database and the copy.
#
# Usage:  ./scripts/check-backup-restore.sh
#
# Run it while the app is idle: the live counts are read after the dump is taken,
# so a write in between would show up as a difference that is not a fault.
#
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

readonly DB_SERVICE="db"
readonly DB_USER="finance"
readonly LIVE_DB="finance"
readonly SCRATCH_DB="finance_restore"

count_rows() {
  local db="$1"
  docker compose exec -T "$DB_SERVICE" psql --username="$DB_USER" --dbname="$db" \
    --no-align --tuples-only <scripts/sql/row-counts.sql
}

echo "1/3 Taking a backup ..."
dump_file="$(./scripts/backup.sh)"
echo "    $dump_file"

echo "2/3 Restoring it into '$SCRATCH_DB' ..."
./scripts/restore.sh "$dump_file" --database "$SCRATCH_DB" >/dev/null

echo "3/3 Comparing row counts ..."
live="$(count_rows "$LIVE_DB")"
restored="$(count_rows "$SCRATCH_DB")"

if [ "$live" = "$restored" ]; then
  echo "PASS: every table matches"
  printf '%s\n' "$live" | while IFS='|' read -r table rows; do
    printf '    %-22s %s\n' "$table" "$rows"
  done
  exit 0
fi

echo "FAIL: the restored database does not match the live one" >&2
echo "--- live / +++ restored" >&2
diff <(printf '%s\n' "$live") <(printf '%s\n' "$restored") >&2 || true
exit 1
