
Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "   Delivery Intelligence Platform - Startup" -ForegroundColor Cyan
Write-Host "===================================================" -ForegroundColor Cyan

# 1. Check for Docker
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Error "Docker is not installed or not in PATH."
    exit 1
}

# 2. Start Services
Write-Host "`n[1/5] Starting Backend & Monitoring Services..." -ForegroundColor Yellow
docker-compose down --remove-orphans
docker-compose up -d --build

# 3. Wait for Health
Write-Host "`n[2/5] Waiting for services to stabilize (15s)..." -ForegroundColor Yellow
Start-Sleep -Seconds 15

# 4. Migrations & Seeding
Write-Host "`n[3/5] Applying Database Migrations & Seeding Data..." -ForegroundColor Yellow
docker-compose exec -T backend alembic upgrade head
docker-compose exec -T backend python tools/seed_data.py

# 5. Grafana Setup
Write-Host "`n[4/5] Configuring Grafana Access..." -ForegroundColor Yellow
# Reset admin password to ensure access
docker-compose exec -T grafana grafana cli admin reset-admin-password new_bizness123
# Restart Grafana to clear temporary login lockouts after repeated failed attempts
docker-compose restart grafana | Out-Null
Start-Sleep -Seconds 3

# 6. Start Simulation
Write-Host "`n[5/5] Launching Fleet Simulation..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-File", ".\run_simulation.ps1"

# 7. Display Access Info
Write-Host "`n===================================================" -ForegroundColor Green
Write-Host "   PLATFORM READY" -ForegroundColor Green
Write-Host "===================================================" -ForegroundColor Green
Write-Host "1. Backend API      : http://localhost:8000/docs"
Write-Host "2. Grafana          : http://localhost:3500"
Write-Host "   - User           : admin"
Write-Host "   - Password       : new_bizness123"
Write-Host "3. Prometheus       : http://localhost:9090"
Write-Host "---------------------------------------------------"
Write-Host "Traffic simulation is correctly running in the separate window."
Write-Host "Dashboards are provisioned and ready."
