# Delivery Intelligence Platform - Operational Runbook

Comprehensive startup procedures, network configuration, health checks, and verification routines.

---

## 1. Network Configuration Reference

| Parameter | Configuration | Notes |
|---|---|---|
| **Host Machine IP** | `192.168.12.196` | Verified local Wi-Fi interface for physical device connectivity. |
| **Backend API Base** | `http://192.168.12.196:8000` | FastAPI Docker container mapped port. |
| **Dispatcher Web UI** | `http://localhost:5173` | Vite React dispatcher portal. |
| **Metro Bundler** | `http://192.168.12.196:8081` | Expo development server. |

---

## 2. Startup Sequence

Execute across three independent terminal windows.

### Terminal 1: Core Backend & Database Infrastructure
```powershell
cd C:\Projects\DELIVERYINTELLIGENCEPLATFORM
docker compose down
docker compose up -d
docker compose ps