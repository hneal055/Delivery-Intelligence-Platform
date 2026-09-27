Write-Host "Verifying Delivery Intelligence Platform Stack..." -ForegroundColor Cyan

# 1. Check container running status
$containers = docker compose ps --format "{{.Name}} - {{.Status}}"
Write-Host "`nContainer Statuses:" -ForegroundColor Yellow
$containers

# 2. Test backend health endpoint
try {
    $response = Invoke-RestMethod -Uri "http://localhost:8000/health" -Method Get -TimeoutSec 5
    Write-Host "`n[SUCCESS] Backend Health Check Passed: $($response.status)" -ForegroundColor Green
} catch {
    Write-Host "`n[ERROR] Backend Health Check Failed: $_" -ForegroundColor Red
}

# 3. Test active dispatches endpoint
try {
    $dispatches = Invoke-RestMethod -Uri "http://localhost:8000/api/dispatches" -Method Get -TimeoutSec 5
    Write-Host "[SUCCESS] Dispatches API Responding. Active count: $($dispatches.Count)" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Dispatches API Failed: $_" -ForegroundColor Red
}
