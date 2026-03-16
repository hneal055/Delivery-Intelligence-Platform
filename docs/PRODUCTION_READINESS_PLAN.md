# Production Readiness Plan

## Overview
This document outlines the roadmap for moving the Delivery Intelligence Platform from a "Proof of Concept" (MVP) to a production-grade system capable of handling real-world fleet operations.

## Phase A: Security Hardening (Priority: High)
*Critical for protecting user data and preventing unauthorized access.*

### 1. Secrets Management
- [x] **Goal**: Remove hardcoded secrets and basic env vars.
- [ ] **Action**: Integrate a secrets manager (e.g., HashiCorp Vault, AWS Secrets Manager) or use Docker Swarm/Kubernetes secrets validation.
- [x] **Task**: Update `config.py` to fetch secrets from secure storage or file mounts instead of plain environment variables.

### 2. Role-Based Access Control (RBAC)
- [x] **Goal**: Granular permission enforcement.
- [ ] **Action**: Implement a permission dependency in FastAPI.
    - Define permissions: `read:packages`, `write:packages`, `assign:jobs`, `view:all_drivers`.
    - Map Roles (`ADMIN`, `MANAGER`, `DRIVER`) to sets of permissions.
- [x] **Task**: Update `auth.py` and `deps.py` with `has_permission()` checkers.

### 3. API Security
- [x] **Goal**: Prevent abuse.
- [x] **Action**:
    - **Rate Limiting**: Configure Redis-backed rate limiting (move away from memory).
    - **Input Validation**: Sanitize all inputs in Pydantic models (already good, but review regex patterns).
    - **CORS**: Restrict `BACKEND_CORS_ORIGINS` to specific production domains. Explicit `allow_methods` and `allow_headers` enforced (no more wildcard `*`).

---

## Phase B: Infrastructure & Scalability (Priority: High)
*Required to run multiple backend instances for high availability.*

### 1. Redis Implementation
- [x] **Goal**: Shared state across backend replicas.
- [ ] **Action**:
    - **WebSocket Pub/Sub**: Use Redis to broadcast tracking updates to all backend nodes.
    - **Caching**: Cache frequent database queries (e.g., `get_user`, `get_active_drivers`).
- [x] **Task**: Replace in-memory `ConnectionManager` in `websocket.py` with `RedisPubSubManager`.

### 2. Async Task Queue (Celery/Arq)
- [x] **Goal**: Offload blocking operations.
- [ ] **Action**: Move heavy tasks out of the request/response cycle.
    - **Tasks to Move**: ML Inference (`predict_eta`), Image Verification, Email/SMS Sending.
- [x] **Task**: Set up a worker container and define tasks.

### 3. Database Migration & Optimization
- [x] **Goal**: Production SQL setup.
- [ ] **Action**:
    - **PostGIS**: Enable PostGIS extension for optimized geospatial queries (replace some `shapely` logic).
    - **Indexing**: Review and add indices for frequently queried columns (`driver_id`, `status`, `created_at`).
    - **Connection Pooling**: Tune `SQLAlchemy` pool size and timeout settings for production load.

---

## Phase C: Data Integrity & Storage (Priority: Medium)
*Ensures data persistence and reliability.*

### 1. S3 Enforcement
- [x] **Goal**: Persistent file storage.
- [ ] **Action**: Enforce `S3StorageBackend` in production mode.
    - Disable `LocalStorageBackend` when `ENV=production`.
    - Add logic to generate pre-signed URLs for secure frontend access.

### 2. Structured Logging
- [x] **Goal**: Machine-readable logs (JSON).
- [ ] **Action**: Configure logging to output JSON format for ingestion by ELK/Datadog/Splunk.
- [x] **Task**: integrate `structlog` or standard python JSON formatter.

---

## Phase D: DevSecOps & Monitoring (Priority: Medium)
*Tools for maintaining the system.*

### 1. CI/CD Pipeline
- [ ] **Action**: Update GitHub Actions (`ci.yml`) to:
    - Run migrations on deploy.
    - Build and push Docker images to a private registry (BCR/ECR).
    - Run comprehensive integration tests.

### 2. Advanced Monitoring
- [ ] **Action**:
    - **Alerting**: Configure Prometheus Alertmanager for high error rates or latency.
    - **Tracing**: Implement OpenTelemetry for distributed tracing.

## Next Step Recommendation
Begin with **Phase B1 (Redis Implementation)** as it solves the immediate issue of scaling the backend for real-time tracking, which is the core feature of the platform.
'

---

## Phase E: Testing & Quality (Priority: High)
*Automated tests prevent regressions and validate business logic.*

### 1. Unit Test Suite ✅ (Completed 2026-03-16)
- [x] **Security**: JWT encode/decode/expiry/tamper, bcrypt password hashing (`tests/unit/test_security.py`)
- [x] **RBAC**: Role→permission mapping coverage for all three roles (`tests/unit/test_permissions.py`)
- [x] **Geofencing**: `is_in_delivery_zone` boundary and polygon logic (`tests/unit/test_geofencing_unit.py`)
- [x] **Routing**: `RoutingService.optimize_route` nearest-neighbor + 2-Opt cases (`tests/unit/test_routing_service.py`)
- [x] **Notifications**: Channel detection, disabled-mode no-ops, mocked Twilio/SendGrid send paths, error handling (`tests/unit/test_notifications.py`)
- [x] **API Health & CORS**: `/health`, `/secure-ping` auth guard, CORS preflight allowlist enforcement (`tests/unit/test_api_health.py`)
- [x] **Shared fixtures** (`tests/conftest.py`): in-memory SQLite DB, fake JWT users, authenticated AsyncClient helpers

**Result: 43 tests, 100% pass rate, ~1.5s runtime, zero external dependencies required.**

### 2. Integration Tests (Remaining)
- [ ] **Auth flow**: POST `/auth/token` with real DB user, token refresh, invalid credentials
- [ ] **Dispatch flow**: Create job → assign to driver → verify package linkage
- [ ] **Delivery flow**: POST `/delivery/confirm` with mock POD, assert status change
- [ ] **Routing**: POST `/routing/optimize` end-to-end with multiple stops

### 3. CI Pipeline
- [ ] **GitHub Actions**: Run `pytest` on every push/PR
- [ ] **Coverage gate**: Enforce minimum 60% coverage via `pytest-cov`
