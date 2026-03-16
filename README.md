# Delivery Intelligence Platform (Private)

## Overview
The **Delivery Intelligence Platform** is a real-time, intelligent delivery management system designed to optimize the "last mile" of logistics. It serves as a central brain for fleet management, preventing misdeliveries, optimizing driver efficiency, and enhancing customer satisfaction through advanced monitoring, data-driven workflows, and AI verification.

> **Note**: This is a private, proprietary repository. Source code distribution is restricted.

## Core Features
*   **Smart Inventory Tracking**: Real-time package mapping to vehicle sections using `Pydantic` models.
*   **Geospatial Intelligence**: Automated geofencing (using `Shapely` & `Geopandas`) to verify driver location against delivery targets.
*   **Automated Verification**: Proof-of-delivery validation (Photo/Signature) to reduce error rates.
*   **Dynamic Routing**: Instructions and route updates dispatched directly to driver DIAD devices.
*   **Real-time Analytics**: Grafana dashboards for fleet monitoring and operational metrics.
*   **Mobile Driver App**: React Native application for drivers to receive routes, predict ETA (ML-powered), and capture delivery proof.
*   **ML ETA Prediction**: Random Forest Regressor model providing real-time arrival estimates considering distance and traffic load.
*   **Dispatch & Scheduling**: Job creation, assignment, and Kanban board for managing dispatch workflows.
*   **GPS Tracking**: Real-time driver map with route history playback and speed controls.
*   **Proof of Delivery Gallery**: Filterable gallery of delivery proof images with detail views.
*   **Equipment / Barcode Scanning**: Camera-based barcode scanning for equipment check-in/out tracking.

## Technical Stack
*   **Backend**: Python 3.9+, FastAPI, Uvicorn, Arq (Async Worker)
*   **Web Dashboard**: React 19, TypeScript, Vite, Mantine UI, Leaflet Maps
*   **Mobile**: React Native, Expo
*   **Data & ML**: Pandas, Scikit-learn, Shapely, GeoAlchemy2, PostGIS
*   **Infrastructure**: Docker Compose, PostgreSQL + PostGIS, Redis, LocalStack (S3)
*   **Visualization**: Grafana, Prometheus
*   **Testing**: Pytest

## Quick Start Guide

### 1. Daily Development Startup
Run the daily startup script to launch the entire stack (backend, frontend, mobile, and simulation):

```powershell
.\daily_startup.ps1
```

This automated script:
- Pulls latest code from git
- Starts Docker services (PostgreSQL, Redis, Grafana)
- Applies database migrations and seeds test data
- Launches fleet simulation
- Starts web dashboard (Vite)
- Starts mobile Expo server

Once complete, access the services at:
*   **API Docs**: `http://localhost:8000/docs`
*   **Web Dashboard**: `http://localhost:5173`
*   **Grafana**: `http://localhost:3500` (Login: `admin` / `new_bizness123`)
*   **Prometheus**: `http://localhost:9090`

### 2. Backend & Infrastructure Only

If you only need backend services without frontend:

```powershell
.\start_platform.ps1
```

### 3. Fleet Simulation
The startup script automatically launches the simulation in a new window. To run it manually or add additional load:

```powershell
.\run_simulation.ps1 -Drivers 50
```

*Note: The simulation runs indefinitely. Press `Ctrl+C` to stop it.*

### 4. Run Dispatcher Web UI

```bash
cd src/web
npm install
npm run dev
```

Access at `http://localhost:5173`. Login with `dispatcher1` / `dispatcherpassword`.

Pages: Dashboard, Scheduling, Drivers, Packages, Proof Gallery, Tracking, Equipment.

### 5. Run Mobile App (Physical Device)

#### Quick Setup
Auto-configure your local IP for mobile testing:
```powershell
.\configure-mobile-env.ps1
```

#### Manual Setup
1. Copy environment template:
   ```bash
   cd src/mobile
   cp .env.example .env
   ```

2. Edit `.env` and set your PC's LAN IP:
   ```env
   EXPO_PUBLIC_API_HOST=192.168.1.100  # Your PC's IP
   EXPO_PUBLIC_API_PORT=8000
   ```

3. Start Expo dev server:
   ```bash
   npm install
   npm start
   ```

4. Scan QR code with Expo Go app on your iPhone/Android device

**Requirements:**
- Phone and PC must be on the same Wi-Fi network
- Backend must be running (`.\start_platform.ps1`)
- Test credentials: `driver1` / `driverpassword`

See [src/mobile/README.md](src/mobile/README.md) for detailed mobile app documentation.

### 6. Run Tests
Execute the unit test suite (no database or external services required):
```bash
pytest
```

Run with coverage report:
```bash
pytest --cov=src --cov-report=term-missing
```

Run a specific module:
```bash
pytest tests/unit/test_security.py -v
```

**Test suite** (`tests/unit/`):
| File | Coverage |
|------|----------|
| `test_security.py` | JWT encode/decode/expiry, bcrypt hashing |
| `test_permissions.py` | RBAC role → permission mapping |
| `test_geofencing_unit.py` | `is_in_delivery_zone` polygon logic |
| `test_routing_service.py` | Nearest-neighbour + 2-Opt optimizer |
| `test_notifications.py` | Channel detection, Twilio/SendGrid mocked send paths |
| `test_api_health.py` | Health endpoint, secure-ping auth, CORS preflight |
| `test_api_basics.py` | Core API endpoint smoke tests |
| `test_routing_api.py` | Route optimization API |


## Troubleshooting

### WebSocket Disconnects (Docker/Windows)
If you encounter unexpected WebSocket disconnects with the backend:
1. Ensure 'uvicorn[standard]' is installed in backend dependencies.
2. The docker-compose configuration forces the 'asyncio' event loop ('uvicorn ... --loop asyncio') to resolve compatibility issues with 'uvloop' in this environment.

### Mobile App Connection Issues
- Verify backend is running and accessible
- Check `.env` file in `src/mobile/` has correct IP address
- Run `ipconfig` (Windows) or `ifconfig` (Mac/Linux) to find your PC's LAN IP
- Ensure firewall allows connections on port 8000
- Use `.\configure-mobile-env.ps1` for automatic IP detection

