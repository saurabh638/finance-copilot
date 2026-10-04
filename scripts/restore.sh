#!/usr/bin/env bash
#
# Restore a dump into a scratch database. Never over the live one.
#
# Usage:  ./scripts/restore.sh backups/finance-2026-10-04-093012.dump [--database NAME]
#
# The scratch database is dropped and recreated on every run, so nothing else in
# the project may use that name. Replacing the live database is deliberately not
# something this script will do: see README.md for that last-resort sequence.
#
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

readonly DB_SERVICE="db"
readonly DB_USER="finance"
readonly LIVE_DB="finance"
readonly DEFAULT_SCRATCH_DB="finance_restore"

usage() {
  echo "Usage: $0 <dump-file> [--database NAME]" >&2
  echo "  Restores into a scratch database (default: $DEFAULT_SCRATCH_DB)." >&2
  echo "  Refuses to restore over the live '$LIVE_DB' database." >&2
}

dump_file=""
scratch_db="$DEFAULT_SCRATCH_DB"

while [ $# -gt 0 ]; do
  case "$1" in
    --database)
      if [ $# -lt 2 ]; then
        usage
        exit 2
      fi
      scratch_db="$2"
      shift 2
      ;;
    -h | --help)
      usage
      exit 0
      ;;
    *)
      if [ -n "$dump_file" ]; then
        usage
        exit 2
      fi
      dump_file="$1"
      shift
      ;;
  esac
done

if [ -z "$dump_file" ]; then
  usage
  exit 2
fi

if [ ! -f "$dump_file" ]; then
  echo "No such dump: $dump_file" >&2
  exit 1
fi

if [ "$scratch_db" = "$LIVE_DB" ]; then
  echo "Refusing to restore over the live '$LIVE_DB' database." >&2
  echo "Restore into a scratch database, check it, then promote it deliberately (see README.md)." >&2
  exit 1
fi

echo "Checking that $dump_file can be read ..."
if ! docker compose exec -T "$DB_SERVICE" pg_restore --list <"$dump_file" >/dev/null; then
  echo "That file is not a readable dump. Nothing was restored." >&2
  exit 1
fi

echo "Recreating the scratch database '$scratch_db' ..."
docker compose exec -T "$DB_SERVICE" psql --username="$DB_USER" --dbname=postgres --quiet \
  --command="DROP DATABASE IF EXISTS \"$scratch_db\" WITH (FORCE)"
docker compose exec -T "$DB_SERVICE" psql --username="$DB_USER" --dbname=postgres --quiet \
  --command="CREATE DATABASE \"$scratch_db\""

echo "Restoring '$dump_file' into '$scratch_db' ..."
docker compose exec -T "$DB_SERVICE" pg_restore \
  --username="$DB_USER" --dbname="$scratch_db" --exit-on-error --no-owner --no-privileges \
  <"$dump_file"

echo
echo "Rows in '$scratch_db':"
docker compose exec -T "$DB_SERVICE" psql --username="$DB_USER" --dbname="$scratch_db" \
  --no-align --tuples-only <scripts/sql/row-counts.sql

echo
echo "Restored into '$scratch_db'. The live '$LIVE_DB' database was not touched."
