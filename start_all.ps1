# =====================================================================
# Delivery Intelligence Platform - Master Autonomous Startup Agent
# =====================================================================
$ErrorActionPreference = "Stop"

Write-Host "====================================================" -ForegroundColor Cyan
Write-Host " [Agent] Starting Full Platform & UI Orchestration" -ForegroundColor Cyan
Write-Host "====================================================" -ForegroundColor Cyan

Write-Host " [1/5] Scrubbing old containers and freeing ports..." -ForegroundColor Yellow
docker compose down --volumes --remove-orphans
Stop-Process -Name "node", "vite", "python", "uvicorn" -Force -ErrorAction SilentlyContinue

Write-Host " [2/5] Spinning up Docker infrastructure..." -ForegroundColor Yellow
docker compose up -d

Write-Host " [3/5] Waiting for database health check..." -ForegroundColor Yellow
$dbHealthy = $false
$retries = 0
while (-not $dbHealthy -and $retries -lt 15) {
    $status = docker inspect --format="{{.State.Health.Status}}" delivery_db 2>$null
    if ($status -eq "healthy") {
        $dbHealthy = $true
    } else {
        Start-Sleep -Seconds 2
        $retries++
    }
}

if (-not $dbHealthy) {
    Write-Host "Database failed to become healthy in time!" -ForegroundColor Red
    exit 1
}

Write-Host " [4/5] Running database migrations and auto-seeding..." -ForegroundColor Yellow
docker compose exec -T backend alembic upgrade head

docker compose exec -T backend python -c @"
import asyncio
from src.backend.core.database import get_db
from src.backend.services.user_service import get_password_hash, create_user
from src.backend.models.sql_models import User as UserSQL, Driver as DriverSQL
from src.backend.models.domain import UserCreate, UserRole
from sqlalchemy import select

async def run():
    async for db in get_db():
        result = await db.execute(select(UserSQL).where(UserSQL.username == 'admin'))
        user = result.scalars().first()
        hashed_admin = get_password_hash('adminpassword')
        if user:
            user.hashed_password = hashed_admin
        else:
            await create_user(db, UserCreate(username='admin', password='adminpassword', email='admin@diplatform.com'), role=UserRole.ADMIN)

        valid_cols = [c.name for c in DriverSQL.__table__.columns]
        hashed_driver = get_password_hash('driverpassword')
        
        for i in range(1, 51):
            d_id = f'D{i:03d}'
            d_res = await db.execute(select(DriverSQL).where(DriverSQL.id == d_id))
            if not d_res.scalars().first():
                driver_args = {'id': d_id}
                if 'name' in valid_cols: driver_args['name'] = f'Driver {i}'
                if 'status' in valid_cols: driver_args['status'] = 'active'
                new_driver = DriverSQL(**driver_args)
                if hasattr(new_driver, 'current_lat'): new_driver.current_lat = 41.8781
                if hasattr(new_driver, 'current_lng'): new_driver.current_lng = -87.6298
                db.add(new_driver)

            u_res = await db.execute(select(UserSQL).where(UserSQL.username == d_id))
            if not u_res.scalars().first():
                db.add(UserSQL(username=d_id, email=f'{d_id.lower()}@diplatform.com', hashed_password=hashed_driver, role='driver', is_active=True))

        await db.commit()
        break

asyncio.run(run())
"@

Write-Host " [5/5] Launching UI Dashboard at http://localhost:5173..." -ForegroundColor Yellow
Start-Sleep -Seconds 3
Start-Process "http://localhost:5173"

Write-Host "`n====================================================" -ForegroundColor Green
Write-Host " Platform & UI Dashboards are fully online and ready!" -ForegroundColor Green
Write-Host "====================================================" -ForegroundColor Green
