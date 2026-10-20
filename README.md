# Delivery Intelligence Platform (DIP)

> **Proprietary Software**
>
> © Chicago Cargo Courier LLC
>
> Internal Use Only
>
> Source code distribution is restricted.
>
> **README Version:** 2.0
>
> **Platform Status:** Operational Foundation Established ✅
>
> **Last Updated:** October 2026

---

# Table of Contents

- [Local Development and Account Recovery](#local-development-and-account-recovery)
- [Executive Summary](#executive-summary)
- [Current Operational Status](#current-operational-status)
- [Architecture](#architecture)
- [Core Capabilities](#core-capabilities)
- [Testing Guide](#testing-guide)
- [Historical Recovery Notes](#historical-recovery-notes)
- [Future Roadmap](#future-roadmap)
- [Project Status](#project-status)

---

# Local Development and Account Recovery

Run Docker Desktop first. From the repository root, start the local stack and
check backend health:

```powershell
.\scripts\dev\start.ps1
Invoke-RestMethod http://localhost:8000/health
```

The dashboard is at `http://localhost:5173`; the backend health endpoint is
`http://localhost:8000/health`. Check `/health`, not the backend site root.
For service diagnostics, use `docker compose ps` and
`docker compose logs backend --tail 100`.

## Reset or create an account

Reset a password using the **exact existing username**. The command prompts
for the new password without displaying it; passwords must be at least 10
characters:

```powershell
docker exec -it delivery_backend python -m src.scripts.set_user_password dispatcher1
docker exec -it delivery_backend python -m src.scripts.set_user_password admin
docker exec -it delivery_backend python -m src.scripts.set_user_password driver1
```

These are examples: usernames depend on the current database. A role name
(`dispatcher`, `admin`, or `driver`) is not automatically a username, and a
driver label such as `D001` works only if an account with that username exists.
To list the configured accounts:

```powershell
docker exec delivery_db psql -U postgres -d delivery -c "SELECT username, role, is_active FROM users ORDER BY username;"
```

Resetting does not create a missing account. To create an admin account if it
does not exist, run:

```powershell
docker exec -it delivery_backend python -m src.scripts.create_user admin admin
```

The creation script prompts for a password. The accepted roles are `driver`,
`dispatcher`, `manager`, and `admin`. Never put real passwords in source,
documentation, screenshots, or command history. Reset any password that has
been exposed.

## Driver app and web troubleshooting

Run Expo commands from `src\mobile`, not the repository root:

```powershell
Set-Location src\mobile
npm run go
```

The phone and office PC must be on the same Wi-Fi for local development. If
the PC's IP changes, run `.\scripts\dev\configure-mobile-env.ps1` from the
repository root, restart Expo with `npx expo start -c`, and verify the
`[API Client] baseURL` log points to `http://<office-PC-IP>:8000`. To run the
mobile project in a PC browser, use `npx expo start -c --web` from `src\mobile`.
If Expo reports missing web packages, run
`npx expo install react-native-web react-dom` from that same directory.

The web client calls `/api/auth/token`; the frontend Nginx proxy strips the
`/api` prefix before forwarding the request to backend `/auth/token`. If web
login still returns 405 or shows stale frontend behavior, rebuild the
frontend and hard-refresh the browser:

```powershell
docker compose up -d --build frontend
```

`401 Unauthorized` for intentionally invalid credentials is an expected
authentication response; it confirms the request reached the login endpoint,
but does not verify valid account credentials. See the
[Operations Manual](docs/manuals/OPERATIONS_MANUAL.md) for detailed recovery
steps.

## Customer SMS status

DIP supports background Twilio texts for out-for-delivery and delivered
milestones. The backend receives Twilio settings through Docker Compose;
blank settings keep SMS disabled. Trust Hub business-profile approval alone
does not complete sender registration: finish the applicable A2P 10DLC
campaign registration or toll-free verification before testing. Configure
credentials privately in `.env` (production) or `.env.backend` (local
development), then follow the safe test steps in the
[Operations Manual](docs/manuals/OPERATIONS_MANUAL.md#11-customer-tracking-link-and-texts).
Use the existing company phone for calls for now; this SMS phase does not
publish a new call number.

# Executive Summary

The **Delivery Intelligence Platform (DIP)** is a containerized logistics intelligence platform built to optimize last-mile delivery operations through real-time tracking, dispatch management, route optimization, proof-of-delivery verification, geospatial intelligence, and predictive analytics.

The platform serves as the operational backbone for fleet management, driver telemetry, dispatch coordination, route intelligence, and delivery execution.

Current platform capabilities include:

- Real-time fleet visibility
- Dispatch workflow management
- Geospatial route intelligence
- Proof-of-delivery verification
- ETA prediction and analytics
- GPS tracking and telemetry
- OAuth2/JWT security
- PostgreSQL/PostGIS spatial services
- Mobile driver workflows
- Monitoring and observability

---

# Current Operational Status

| Component | Status |
|------------|----------|
| Docker Infrastructure | ✅ Operational |
| Backend API | ✅ Operational |
| PostgreSQL | ✅ Operational |
| PostGIS | ✅ Operational |
| Redis | ✅ Operational |
| Swagger UI | ✅ Operational |
| OpenAPI Generation | ✅ Operational |
| Alembic Migrations | ✅ Operational |
| Authentication | ✅ Operational |
| JWT Authorization | ✅ Operational |
| Database Seeding | ✅ Operational |
| Dispatch Validation | 🔄 In Progress |
| Tracking Validation | ⬜ Pending |
| Routing Validation | ⬜ Pending |
| Analytics Validation | ⬜ Pending |
| Production Hardening | ⬜ Pending |

---

# Architecture

```text
                    Delivery Intelligence Platform

 ┌────────────────────────────────────────────────────┐
 │                    Frontend UI                     │
 └────────────────────────────────────────────────────┘
                          │
                          ▼

 ┌────────────────────────────────────────────────────┐
 │                 FastAPI Backend                    │
 └────────────────────────────────────────────────────┘
                │                │
                ▼                ▼

       ┌─────────────────┐   ┌─────────────────┐
       │      Redis      │   │   PostgreSQL    │
       │   Pub / Sub     │   │     PostGIS     │
       └─────────────────┘   └─────────────────┘
                │
                ▼

     ┌─────────────────────────────┐
     │ Analytics & ML Services     │
     └─────────────────────────────┘
                │
                ▼

     ┌─────────────────────────────┐
     │ Route Optimization Engine   │
     └─────────────────────────────┘
```

---

# Core Capabilities

The Delivery Intelligence Platform delivers end-to-end operational intelligence across logistics, fleet management, dispatch, routing, proof-of-delivery validation, and predictive analytics.

---

## Last-Mile Logistics Intelligence
DIP serves as the operational intelligence layer for delivery execution, providing complete visibility throughout the delivery lifecycle.


```
 
Fix:
 
```powershell
python -m tools.seed_dev_data
```

(Needs the passwords in `.env.backend`; run `.\scripts\dev\setup_secrets.ps1` first. `.\scripts\dev\start.ps1` runs this automatically.)

 
---
 
## Web Authentication

The browser sends credentials to `/api/auth/token`; frontend Nginx removes
`/api` when forwarding to backend `/auth/token`. If this request returns 405,
rebuild the frontend and hard-refresh the browser as described in
[Local Development and Account Recovery](#local-development-and-account-recovery).
For an unknown username or forgotten password, follow the account recovery
steps in that section. The login request does not use a bearer token; one is
returned only after valid credentials authenticate.

---
# Testing Guide
 
## Run All Tests
 
```powershell
pytest
```
 
## Coverage Report
 
```powershell
pytest --cov=src --cov-report=term-missing
```
 
## Specific Test
 
```powershell
pytest tests/unit/test_security.py -v
```
 
---
 
# Incident Recovery Timeline
 
## Original Failure
 
```text
Docker build failure
requirements.txt dependency failures
```
 
## Root Causes
 
- Linux dependency issues
- Database configuration drift
- Missing schema
- Missing users table
- Missing seed data
 
## Recovery Milestones
 
✅ Docker Build Recovered
 
✅ Services Operational
 
✅ Schema Recovered
 
✅ Users Table Restored
 
✅ Seed Data Loaded
 
✅ Authentication Working
 
✅ JWT Generation Working
 
✅ Swagger Operational
 
---
 
# Historical Recovery Notes

The notes below predate the frontend API proxy correction documented above.
They are retained as recovery history and should not be read as the current
authentication status.
 
## Dispatch Dashboard Authentication
 
Endpoint:
 
```http
GET /dispatch/dispatch/dashboard/summary
```
 
Current Behavior:
 
```json
{
"detail": "Not authenticated"
}
```
 
Status:
 
🔄 Investigation In Progress
 
Potential Areas:
 
- JWT propagation
- Swagger authorization handling
- Router security configuration
 
---
 
# Historical Validation Priorities
 
## Priority 1
 
```http
GET /auth/users/me
```
 
Validate authenticated user context.
 
## Priority 2
 
```http
GET /dispatch/dispatch/dashboard/summary
```
 
Validate dispatch dashboard authorization.
 
## Priority 3
 
```http
GET /dispatch/dispatch/drivers
```
 
Validate database-backed dispatch records.
 
## Priority 4
 
```http
POST /dispatch/dispatch/jobs
```
 
Validate dispatch workflow management.
 
---
 
# Future Roadmap
 
## Mobile Experience
 
- Driver mobile workflows
- Push notifications
- Offline operation
- Mobile POD processing
 
## Command Center
 
- Live telemetry dashboards
- Fleet heat maps
- Real-time alerting
- KPI visualization
 
## Advanced Analytics
 
- Demand forecasting
- Capacity planning
- Risk prediction
- Performance scoring
 
## AI & Predictive Intelligence
 
- Intelligent dispatch recommendations
- Driver optimization
- Predictive routing
- Delivery risk mitigation
 
---
 
# Project Status
 
```text
Infrastructure Recovery ✅ COMPLETE
Container Recovery ✅ COMPLETE
Database Recovery ✅ COMPLETE
Migration Recovery ✅ COMPLETE
Authentication Recovery ✅ COMPLETE
Dispatch Validation 🔄 IN PROGRESS
Tracking Validation ⬜ PENDING
Routing Validation ⬜ PENDING
Analytics Validation ⬜ PENDING
Production Readiness ⬜ PENDING
```
 
---
 
**README Version:** 2.0
 
**Platform State:** Operational Foundation Established ✅
 
**Current Milestone:** Dispatch Functional Validation 🔄
 
**Next Major Milestone:** End-to-End Operational Workflow Validation 🚀
