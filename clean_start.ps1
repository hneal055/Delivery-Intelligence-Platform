# =====================================================================
# Delivery Intelligence Platform - Clean Environment Startup Script
# =====================================================================

Write-Host " [1/4] Tearing down Docker containers and volumes..." -ForegroundColor Cyan
docker compose down --volumes --remove-orphans

# Stop any rogue Docker instances if present
$runningContainers = docker ps -a -q
if ($runningContainers) {
    Write-Host " [2/4] Forcibly stopping remaining containers..." -ForegroundColor Cyan
    docker stop $runningContainers 2>&1 | Out-Null
    docker rm $runningContainers 2>&1 | Out-Null
}

Write-Host " [3/4] Terminating stray local development processes..." -ForegroundColor Cyan
Stop-Process -Name "node", "vite", "python", "uvicorn" -Force -ErrorAction SilentlyContinue

Write-Host " [4/4] Freeing up critical development ports..." -ForegroundColor Cyan
Get-NetTCPConnection -State Listen | Where-Object { $_.LocalPort -in 8, 8000, 8002, 5173, 3500, 5432 } | ForEach-Object {
    $process = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue
    if ($process) {
        Write-Host "    -> Stopping $($process.Name) (PID: $($process.Id)) on port $($_.LocalPort)" -ForegroundColor Yellow
        Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
    }
}

Write-Host "`nEnvironment is fully scrubbed and ready for a fresh build!" -ForegroundColor Green

# --- START CONTAINER STACK ---
Write-Host " [5/5] Spinning up container stack (PostgreSQL, Redis, Backend)..." -ForegroundColor Cyan
docker compose up -d

# --- AUTOMATED MIGRATIONS & SEEDING ---
Write-Host "Waiting for backend services to initialize..." -ForegroundColor Cyan
Start-Sleep -Seconds 8

Write-Host "Running Alembic database migrations..." -ForegroundColor Cyan
docker compose exec backend alembic upgrade head

Write-Host "Seeding admin, dispatcher, and driver accounts & profiles (D001-D050)..." -ForegroundColor Cyan
docker compose exec backend python -c @"
import asyncio
from src.backend.core.database import get_db
from src.backend.services.user_service import get_password_hash, create_user
from src.backend.models.sql_models import User as UserSQL, Driver as DriverSQL
from src.backend.models.domain import UserCreate, UserRole
from sqlalchemy import select

async def run():
    async for db in get_db():
        # 1. Ensure Admin Account Exists
        result = await db.execute(select(UserSQL).where(UserSQL.username == 'admin'))
        user = result.scalars().first()
        hashed_admin = get_password_hash('adminpassword')
        if user:
            user.hashed_password = hashed_admin
            print('Updated existing admin password.')
        else:
            await create_user(db, UserCreate(username='admin', password='adminpassword', email='admin@diplatform.com'), role=UserRole.ADMIN)
            print('Created admin user.')

        # 2. Seed Drivers D001-D050 safely handling valid columns only
        valid_cols = [c.name for c in DriverSQL.__table__.columns]
        hashed_driver = get_password_hash('driverpassword')
        
        for i in range(1, 51):
            d_id = f'D{i:03d}'
            
            # Check/Create Driver Profile
            d_res = await db.execute(select(DriverSQL).where(DriverSQL.id == d_id))
            if not d_res.scalars().first():
                driver_args = {'id': d_id}
                if 'name' in valid_cols: driver_args['name'] = f'Driver {i}'
                if 'status' in valid_cols: driver_args['status'] = 'active'
                
                new_driver = DriverSQL(**driver_args)
                
                # Safely assign location fields post-init if they exist as attributes
                if hasattr(new_driver, 'current_lat'): new_driver.current_lat = 41.8781
                if hasattr(new_driver, 'current_lng'): new_driver.current_lng = -87.6298
                if hasattr(new_driver, 'lat'): new_driver.lat = 41.8781
                if hasattr(new_driver, 'lng'): new_driver.lng = -87.6298
                
                db.add(new_driver)

            # Check/Create User Account for Simulator Authentication
            u_res = await db.execute(select(UserSQL).where(UserSQL.username == d_id))
            if not u_res.scalars().first():
                db.add(UserSQL(
                    username=d_id,
                    email=f'{d_id.lower()}@diplatform.com',
                    hashed_password=hashed_driver,
                    role='driver',
                    is_active=True
                ))

        await db.commit()
        print('Seeded drivers D001-D050 and auth accounts successfully!')
        break

asyncio.run(run())
"@

Write-Host "Environment is fully set up, migrated, and seeded! Ready for action." -ForegroundColor Green