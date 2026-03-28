#!/bin/sh
set -eu

until mc alias set local http://minio:9000 "${MINIO_ROOT_USER:-minioadmin}" "${MINIO_ROOT_PASSWORD:-minioadmin}" >/dev/null 2>&1; do
  echo "waiting for minio..."
  sleep 2
done

mc mb local/reels-assets --ignore-existing
mc mb local/reels-quarantine --ignore-existing
mc mb local/reels-temp --ignore-existing
mc mb local/reels-models --ignore-existing
mc ilm rule add local/reels-temp --expire-days 1 || true

echo "minio buckets ready"
