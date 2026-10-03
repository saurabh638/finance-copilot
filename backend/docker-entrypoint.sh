#!/bin/sh
# Apply database migrations, then run the given command (uvicorn by default).
set -e

alembic upgrade head

exec "$@"
