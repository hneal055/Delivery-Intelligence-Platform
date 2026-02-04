# Delivery Intelligence Platform

## Overview
The **Delivery Intelligence Platform** is a real-time, intelligent delivery management system designed to optimize the "last mile" of logistics. It serves as a central brain for fleet management, preventing misdeliveries, optimizing driver efficiency, and enhancing customer satisfaction through advanced monitoring, data-driven workflows, and AI verification.

## Core Features
*   **Smart Inventory Tracking**: Real-time package mapping to vehicle sections using `Pydantic` models.
*   **Geospatial Intelligence**: Automated geofencing (using `Shapely` & `Geopandas`) to verify driver location against delivery targets.
*   **Automated Verification**: Proof-of-delivery validation (Photo/Signature) to reduce error rates.
*   **Dynamic Routing**: Instructions and route updates dispatched directly to driver DIAD devices.
*   **Real-time Alerts**: Instant notifications for customers (SMS/Email) and fleet managers via the Notification Service.

## Technical Stack
*   **Backend**: Python 3.8+, FastAPI, Uvicorn
*   **Data & ML**: Pandas, Scikit-learn, Shapely
*   **Infrastructure**: Docker, Kubernetes, AWS (CloudFormation)
*   **Testing**: Pytest, Pytest-cov
*   **Security**: API Key authentication for DIAD devices

## Quick Start Guide

### How to install dependencies
```bash
pip install -r requirements.txt
```

### How to start the app
```bash
uvicorn src.backend.api.main:app --reload
```

### How to run with Docker
```bash
docker-compose up
```

### How to run tests
```bash
pytest
```

## Detailed Installation

1.  **Clone the repository**
    ```bash
    git clone https://github.com/hneal055/Delivery-Intelligence-Platofrm.git
    cd Delivery-Intelligence-Platofrm
    ```

2.  **Set up the environment** (Windows)
    Run the setup script to create the virtual environment:
    ```powershell
    ./Setup_PythonEnvironment.ps1
    ```

3.  **Explore the API**
    Open your browser to: `http://127.0.0.1:8000/docs`

## Project Structure
```text
DeliveryIntelligencePlatform/
├── src/
│   ├── analytics/          # ML models, Geofencing, Image Analysis
│   ├── backend/            # FastAPI App, Routes, Services, Models
│   └── scripts/            # ETL and Deployment scripts
├── config/                 # Environment and logging configs
├── data/                   # Raw/Processed data storage
├── docs/                   # Architecture and Requirements documentation
├── infrastructure/         # Docker/K8s/AWS IaC
├── tests/                  # Unit and Integration tests
└── tools/                  # Simulation and profiling tools
```

## Security
This project uses header-based API Key authentication for device endpoints (`secure-ping`).
*   **Header**: `X-DIAD-Token`
*   **Default Dev Key**: `dev-secret-key-123`
