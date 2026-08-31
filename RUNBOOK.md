Markdown# Delivery Intelligence Platform - Operational Runbook



Comprehensive startup procedures, network configuration, health checks, and verification routines.



\---



\## 1. Network Configuration Reference



| Parameter | Configuration | Notes |

|---|---|---|

| \*\*Host Machine IP\*\* | `192.168.12.196` | Verified local Wi-Fi interface for physical device connectivity. |

| \*\*Backend API Base\*\* | `http://192.168.12.196:8000` | FastAPI Docker container mapped port. |

| \*\*Dispatcher Web UI\*\* | `http://localhost:5173` | Vite React dispatcher portal. |

| \*\*Metro Bundler\*\* | `http://192.168.12.196:8081` | Expo development server. |



\---



\## 2. Startup Sequence



Execute across three independent terminal windows.



\### Terminal 1: Core Backend \& Database Infrastructure

```powershell

cd C:\\Projects\\DELIVERYINTELLIGENCEPLATFORM

docker compose down

docker compose up -d

docker compose ps

Terminal 2: Web Dispatcher PortalPowerShellcd C:\\Projects\\DELIVERYINTELLIGENCEPLATFORM\\src\\web

npm run dev

Access URL: http://localhost:5173Default Dispatcher Login: dispatcher1 / <DISPATCHER\_PASSWORD\_EXAMPLE>Terminal 3: Mobile Client (Expo Metro)PowerShellcd C:\\Projects\\DELIVERYINTELLIGENCEPLATFORM\\src\\mobile

npx expo start --clear

Press s if needed to ensure Expo Go mode is active.Scan the generated QR code via the Expo Go app on your physical mobile device.Default Driver Login: driver1 / <DRIVER\_PASSWORD\_EXAMPLE>3. Database Verification \& SeedingVerify driver records and seed active baseline coordinates in PostgreSQL:PowerShell# Check driver presence in delivery\_db

docker exec -it delivery\_db psql -U postgres -d delivery\_db -c "SELECT id, name, status, current\_lat, current\_lon FROM drivers WHERE id = 'D001';"



\# Seed or reset D001 baseline coordinates

docker exec -it delivery\_db psql -U postgres -d delivery\_db -c "INSERT INTO drivers (id, name, status, current\_lat, current\_lon) VALUES ('D001', 'Driver 001', 'active', 41.8781, -87.6298) ON CONFLICT (id) DO UPDATE SET status = 'active', current\_lat = 41.8781, current\_lon = -87.6298;"

4\. End-to-End Verification ChecklistTest ItemActionExpected ResultDriver StatusOpen mobile client home screenTop header displays D001 • ONLINE with a green indicator.Telemetry SyncCheck Web Dispatcher mapDriver D001 appears active on the Chicago map with live GPS marker.Manifest SyncPull down list or tap 🔄 SyncManifest refreshes and fires heartbeat payload to /tracking/D001/location.Barcode ScannerTap 📷 Scan / scan QR or chip pkg-001Confirmation dialog appears: Confirm \& Deliver.Proof UploadConfirm scan dialogPackage transitions to DELIVERED locally and logs to /delivery/confirm.5. Troubleshooting ReferenceDriver shows OFFLINE or SYNCING...:Verify client.js is targeting port 8000 (http://192.168.12.196:8000), not 8002.Confirm the mobile device is on the same local Wi-Fi subnet (192.168.12.x).Database Connection Errors:Ensure the target database name in psql commands is delivery\_db (not delivery\_platform).

