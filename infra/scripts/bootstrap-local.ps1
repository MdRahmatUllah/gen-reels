param(
  [switch]$Gpu
)

$composeArgs = @("-f", "infra/compose/docker-compose.yml")
if ($Gpu) {
  $composeArgs += @("-f", "infra/compose/docker-compose.gpu.yml")
}

docker compose @composeArgs up -d --build
if ($LASTEXITCODE -ne 0) {
  exit $LASTEXITCODE
}

docker compose @composeArgs exec api uv run alembic upgrade head
if ($LASTEXITCODE -ne 0) {
  exit $LASTEXITCODE
}

docker compose @composeArgs exec api uv run reels-cli seed
if ($LASTEXITCODE -ne 0) {
  exit $LASTEXITCODE
}

Write-Host "Local stack bootstrapped."
& "$PSScriptRoot/print-local-urls.ps1"

