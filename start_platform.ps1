Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "   Delivery Intelligence Platform - Startup" -ForegroundColor Cyan
Write-Host "===================================================" -ForegroundColor Cyan

# 1. Check for Docker
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Error "Docker is not installed or not in PATH."
    exit 1
}

# 2. Start Services
Write-Host "`n[1/3] Starting Backend & Monitoring Services..." -ForegroundColor Yellow
docker-compose down
docker-compose up -d --build

# 3. Wait for Health (Simple pause for MVP, logic can be improved)
Write-Host "`n[2/3] Waiting for services to stabilize (15s)..." -ForegroundColor Yellow
Start-Sleep -Seconds 15

# 4. Display Access Info
Write-Host "`n[3/3] Platform Ready!" -ForegroundColor Green
Write-Host "---------------------------------------------------"
Write-Host "API Documentation : http://localhost:8000/docs"
Write-Host "Grafana Dashboards: http://localhost:3500 (admin/admin)"
Write-Host "Prometheus        : http://localhost:9090"
Write-Host "---------------------------------------------------"
Write-Host "`nNext Steps:"
Write-Host "Run the fleet simulator: .\run_simulation.ps1"
