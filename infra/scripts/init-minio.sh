#!/bin/sh
set -eu

MINIO_URL="${MINIO_URL:-http://minio:9000}"
MINIO_ROOT_USER="${MINIO_ROOT_USER:-minioadmin}"
MINIO_ROOT_PASSWORD="${MINIO_ROOT_PASSWORD:-minioadmin}"
MINIO_BUCKET_ASSETS="${MINIO_BUCKET_ASSETS:-reels-assets}"
MINIO_BUCKET_QUARANTINE="${MINIO_BUCKET_QUARANTINE:-reels-quarantine}"
MINIO_BUCKET_TEMP="${MINIO_BUCKET_TEMP:-reels-temp}"
MINIO_BUCKET_MODELS="${MINIO_BUCKET_MODELS:-reels-models}"

until mc alias set local "${MINIO_URL}" "${MINIO_ROOT_USER}" "${MINIO_ROOT_PASSWORD}" >/dev/null 2>&1; do
  echo "waiting for minio..."
  sleep 2
done

mc mb "local/${MINIO_BUCKET_ASSETS}" --ignore-existing
mc mb "local/${MINIO_BUCKET_QUARANTINE}" --ignore-existing
mc mb "local/${MINIO_BUCKET_TEMP}" --ignore-existing
mc mb "local/${MINIO_BUCKET_MODELS}" --ignore-existing
mc anonymous set none "local/${MINIO_BUCKET_ASSETS}" >/dev/null 2>&1 || true
mc anonymous set none "local/${MINIO_BUCKET_QUARANTINE}" >/dev/null 2>&1 || true
mc anonymous set none "local/${MINIO_BUCKET_TEMP}" >/dev/null 2>&1 || true
mc anonymous set none "local/${MINIO_BUCKET_MODELS}" >/dev/null 2>&1 || true
mc ilm rule add "local/${MINIO_BUCKET_TEMP}" --expire-days 1 >/dev/null 2>&1 || true

echo "minio buckets ready"

