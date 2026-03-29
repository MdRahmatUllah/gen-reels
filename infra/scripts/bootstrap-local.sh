#!/usr/bin/env sh
set -eu

COMPOSE_ARGS="-f infra/compose/docker-compose.yml"

if [ "${1:-}" = "--gpu" ]; then
  COMPOSE_ARGS="$COMPOSE_ARGS -f infra/compose/docker-compose.gpu.yml"
fi

docker compose $COMPOSE_ARGS up -d --build
docker compose $COMPOSE_ARGS exec api uv run alembic upgrade head
docker compose $COMPOSE_ARGS exec api uv run reels-cli seed

echo "Local stack bootstrapped."
sh "$(dirname "$0")/print-local-urls.sh"

