# Smoke test Render API with long timeouts (cold start + model load).
# Usage: .\scripts\render-smoke.ps1
#   Optional: $env:RENDER_API = "https://your-service.onrender.com"

$Base = if ($env:RENDER_API) { $env:RENDER_API.TrimEnd('/') } else { "https://research-search-platform.onrender.com" }

Write-Host "1) Health (timeout 300s)..." -ForegroundColor Cyan
Invoke-RestMethod -Uri "$Base/api/health" -TimeoutSec 300

Write-Host "2) Ready check (timeout 300s)..." -ForegroundColor Cyan
Invoke-RestMethod -Uri "$Base/api/ready" -TimeoutSec 300

Write-Host "3) Warm (timeout 60s)..." -ForegroundColor Cyan
Invoke-RestMethod -Uri "$Base/api/warm" -Method POST -TimeoutSec 60

Write-Host "4) Poll ready until true (max ~20 min)..." -ForegroundColor Cyan
$deadline = (Get-Date).AddMinutes(20)
while ((Get-Date) -lt $deadline) {
  Start-Sleep -Seconds 10
  $r = Invoke-RestMethod -Uri "$Base/api/ready" -TimeoutSec 300
  Write-Host "  embedding_ready: $($r.embedding_ready)"
  if ($r.embedding_ready) { break }
}

Write-Host "5) Search (timeout 180s)..." -ForegroundColor Cyan
Invoke-RestMethod `
  -Uri "$Base/api/search" `
  -Method POST `
  -ContentType "application/json" `
  -Body '{"query":"battery thermal","doc_type":"both","limit":10}' `
  -TimeoutSec 180

Write-Host "Done." -ForegroundColor Green
