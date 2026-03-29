$services = @(
  @{ Name = "Frontend"; Url = "http://localhost:5173" },
  @{ Name = "API"; Url = "http://localhost:8000" },
  @{ Name = "MinIO API"; Url = "http://localhost:9000" },
  @{ Name = "MinIO Console"; Url = "http://localhost:9001" },
  @{ Name = "Mailpit"; Url = "http://localhost:8025" }
)

Write-Host ""
Write-Host "Local service URLs"
Write-Host "------------------"
foreach ($service in $services) {
  Write-Host ("{0,-14} {1}" -f "$($service.Name):", $service.Url)
}

