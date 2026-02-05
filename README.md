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
*   **Mobile Driver App**: React Native application for drivers to receive routes and capturing delivery proof.

## Technical Stack
*   **Backend**: Python 3.8+, FastAPI, Uvicorn
*   **Mobile**: React Native, Expo
*   **Data & ML**: Pandas, Scikit-learn, Shapely
*   **Infrastructure**: Docker, Kubernetes, AWS (CloudFormation)
*   **Visualization**: Grafana, Prometheus
*   **Testing**: Pytest, Pytest-cov

## Quick Start Guide

### 1. Start Support Services (Docker)
Start the database, Grafana, and backend services:
```bash
docker-compose up --build
```
*   **Backend API**: `http://localhost:8000/docs`
*   **Grafana Dashboard**: `http://localhost:3500` (Default: `admin`/`admin`)

### 2. Run Backend Locally (Optional - for Dev)
If you need to run the backend outside of Docker:
```bash
# Install dependencies
pip install -r requirements.txt

# Start the server
uvicorn src.backend.api.main:app --reload
```

### 3. Run Mobile App
Navigate to the mobile directory and start the Expo development server:
```bash
cd src/mobile
npm install
npm run web  # Run in browser
# OR
npm run android # Run on Android emulator
```

## Project Structure
```text
DeliveryIntelligencePlatform/
├── src/
│   ├── analytics/          # ML models, Geofencing, Image Analysis
│   ├── backend/            # FastAPI App, Routes, Services, Models
│   ├── mobile/             # React Native Driver Application
│   └── scripts/            # ETL and Deployment scripts
├── config/                 # Environment and logging configs
│   ├── grafana/            # Dashboards and Datasource provision configs
├── data/                   # Raw/Processed data storage
├── docs/                   # Architecture and Requirements documentation
├── infrastructure/         # Docker/K8s/AWS IaC
├── tests/                  # Unit and Integration tests
└── tools/                  # Simulation and profiling tools
```

## Security
Currently uses header-based API Key authentication for device endpoints (`secure-ping`).
*   **Header**: `X-DIAD-Token`
*   **Default Dev Key**: `dev-secret-key-123`

## Simulation & Load Testing
To simulate fleet activity and stress-test the API:

```bash
# Ensure backend is running, then in a new terminal:
python tools/simulators/fleet_sim.py --drivers 50
```

## Troubleshooting
- **Grafana Login**: If `admin/admin` does not work, check the `docker-compose.yml` for `GF_SECURITY_ADMIN_PASSWORD`.
- **Mobile Dependencies**: If `npm install` fails, remove `node_modules` and `package-lock.json` and try again.

