#!/usr/bin/env sh
set -eu

cat <<'EOF'

Local service URLs
------------------
Frontend:       http://localhost:5173
API:            http://localhost:8000
MinIO API:      http://localhost:9000
MinIO Console:  http://localhost:9001
Mailpit:        http://localhost:8025
EOF

