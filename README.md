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

## Technical Stack
*   **Backend**: Python 3.8+, FastAPI, Uvicorn
*   **Mobile**: React Native, Expo
*   **Data & ML**: Pandas, Scikit-learn, Shapely
*   **Infrastructure**: Docker, Kubernetes, AWS (CloudFormation)
*   **Visualization**: Grafana, Prometheus
*   **Testing**: Pytest

## Quick Start Guide

### 1. Daily Development Startup
We provided a helper script to spin up the entire stack, apply migrations, seed data, and start traffic simulation:

```powershell
.\start_platform.ps1
```

Once complete, access the services at:
*   **API Docs**: `http://localhost:8000/docs`
*   **Grafana**: `http://localhost:3500` (Login: `admin` / `new_bizness123`)
*   **Prometheus**: `http://localhost:9090`

### 2. Fleet Simulation
The startup script automatically launches the simulation in a new window. To run it manually or add additional load:

```powershell
.\run_simulation.ps1 -Drivers 50
```

*Note: The simulation runs indefinitely. Press `Ctrl+C` to stop it.*

### 3. Run Mobile App
To test the driver experience manually:
```bash
cd src/mobile
npx expo start --web
```

### 4. Run Tests
Execute the unit test suite:
```bash
pytest
```


## Troubleshooting

### WebSocket Disconnects (Docker/Windows)
If you encounter unexpected WebSocket disconnects with the backend:
1. Ensure 'uvicorn[standard]' is installed in backend dependencies.
2. The docker-compose configuration forces the 'asyncio' event loop ('uvicorn ... --loop asyncio') to resolve compatibility issues with 'uvloop' in this environment.

