# Delivery Intelligence Platform

> **Note**: This is a private, proprietary repository for Chicago Cargo Courier LLC. Source code distribution is restricted.

## 🎯 Overview

The **Delivery Intelligence Platform** is a real-time, intelligent delivery management system designed to optimize the "last mile" of logistics. It serves as the central operational brain for fleet management, real-time telemetry streaming, dynamic routing, and automated proof-of-delivery verification.

---

## ✨ Core Features

*   **Smart Inventory Tracking**: Real-time package mapping to vehicle sections using Pydantic models.
*   **Geospatial Intelligence**: Automated geofencing (using Shapely & GeoPandas / PostGIS) to verify driver location against delivery targets.
*   **Automated Verification**: Proof-of-delivery validation (Photo/Signature) including automated image quality checks (resolution, brightness, sharpness).
*   **Real Traffic & ETA Intelligence**: Live traffic-adjusted travel time and distance via the TomTom Routing API, with graceful fallback to synthetic estimates.
*   **Dynamic Routing**: Instructions and route updates dispatched directly to driver devices.
*   **Real-time Analytics**: Grafana and Prometheus telemetry dashboards for fleet monitoring and operational metrics.
*   **Mobile Driver App**: React Native application for drivers to receive routes, view ETAs, and capture delivery proof.
*   **ML ETA Prediction**: Scikit-learn Random Forest Regressor model providing real-time arrival estimates factoring in distance and traffic load.
*   **Dispatch & Scheduling**: Job creation, assignment, and Kanban boards for managing dispatch workflows.
*   **GPS Tracking**: Real-time driver map with route history playback and speed controls.
*   **Proof of Delivery Gallery**: Filterable gallery of delivery proof images with detail views.
*   **Equipment & Barcode Scanning**: Camera-based barcode scanning for equipment check-in/out tracking.

---

## 🛠️ Technical Stack

*   **Backend**: Python 3.11+, FastAPI, Uvicorn, Arq (Async Worker), OpenTelemetry
*   **Web Dashboard**: React, TypeScript, Vite, Mantine UI, Leaflet Maps, Nginx
*   **Mobile**: React Native, Expo
*   **Data & ML**: Pandas, Scikit-learn, Shapely, GeoAlchemy2, PostGIS
*   **External APIs**: TomTom Routing/Traffic API (optional)
*   **Infrastructure**: Docker Compose, PostgreSQL + PostGIS 15, Redis, LocalStack (S3)
*   **Visualization**: Grafana, Prometheus
*   **Testing**: Pytest

---

## 🚀 Quick Start & Operational Scripts

The platform includes automated PowerShell scripts to manage container lifecycles, database resets, and fleet simulations.

### 0. Environment Setup
Copy the environment template and configure your local variables before the first run:
```powershell
cp .env.example .env

Ensure SECRET_KEY, POSTGRES_PASSWORD, and REDIS_PASSWORD are configured.

1. Daily Development Startup
To spin up the existing container stack (PostGIS, Redis, Backend, Web frontend, and monitoring) for daily development:

PowerShell
.\daily_startup.ps1
2. Full Clean Reset & Fresh Build
If you encounter configuration drift, schema changes, or need to purge old volumes and containers for a completely clean slate:

PowerShell
.\clean_start.ps1
3. Run Fleet Simulation
To launch virtual drivers that authenticate against /auth/token and stream live GPS telemetry into PostGIS:

PowerShell
.\run_simulation.ps1 -Drivers 10
(Or run the Python simulator directly: python tools/simulators/fleet_sim.py --drivers 10)

🌐 Access Points & Services
Once your containers are running, you can access the platform services at:

API Documentation (Swagger UI): http://localhost:8002/docs

Web Dispatch Dashboard: http://localhost (or http://localhost:5173 during local dev)

Grafana Telemetry: http://localhost:3500 (Login: admin / see .env)

Prometheus Metrics: http://localhost:9090

🧪 Running Tests
Execute the unit test suite (no database or external services required):

PowerShell
pytest
Run with coverage report:

PowerShell
pytest --cov=src --cov-report=term-missing
Run a specific test module:

PowerShell
pytest tests/unit/test_security.py -v

---

### **Ready to Push?**
Save this clean text to your root `README.md` and run your git commands:
```powershell
git add README.md
git commit -m "Finalize professional README.md with script guides and platform specs"
git pull origin main --rebase
git push -u origin main

