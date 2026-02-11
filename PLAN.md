# Integration Implementation Plan

Four integrations in order: S3, Twilio/SendGrid, Redis, Mapbox. Each is independently toggleable via environment variables with graceful fallback to current behavior.

---

## Phase 1: AWS S3 for Proof-of-Delivery Storage

Replace local filesystem storage with S3. Use LocalStack in Docker for local development.

### 1.1 Add dependencies and config
- **requirements.txt**: Add `boto3>=1.26.0`
- **src/backend/core/config.py**: Add settings:
  - `PROOF_STORAGE: str = os.getenv("PROOF_STORAGE", "local")` — "local" or "s3"
  - `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`, `S3_BUCKET_NAME`, `S3_ENDPOINT_URL` (for LocalStack)
- **docker-compose.yml**: Add `localstack` service (S3-only) on port 4566, add S3 env vars to backend service

### 1.2 Create storage service
- **NEW: src/backend/services/storage.py**:
  - `StorageBackend` (protocol/ABC) with `upload(key, data, content_type) -> str` and `get_url(key) -> str` and `list_files(prefix) -> list`
  - `LocalStorageBackend` — wraps current filesystem logic from delivery.py (PROOFS_BASE_DIR, os.listdir, FileResponse path)
  - `S3StorageBackend` — uses boto3 client: `put_object()` for upload, `generate_presigned_url()` for retrieval (1h expiry), `list_objects_v2()` for listing
  - `get_storage_backend()` factory function — returns S3 or Local based on `settings.PROOF_STORAGE`
  - Singleton `proof_storage = get_storage_backend()`

### 1.3 Modify delivery routes
- **src/backend/api/routes/delivery.py**:
  - Replace `PROOFS_BASE_DIR` filesystem logic with `proof_storage` calls
  - `POST /confirm`: Replace `open(file_path, "wb")` with `proof_storage.upload(key, content, "image/jpeg")`
  - `GET /recent-proofs`: Replace `os.listdir()` with `proof_storage.list_files("proofs/")`; return presigned URLs for S3 or existing `/delivery/proof/` URLs for local
  - `GET /proof/{filename}`: Keep for local backend; S3 mode redirects to presigned URL

### 1.4 Update frontend
- **src/web/src/api/delivery.ts**: `getProofImageUrl()` — if proof `url` starts with `http` (presigned), use directly; otherwise prepend API_URL as today

### 1.5 Verification
- `docker compose build backend && docker compose up -d`
- Confirm LocalStack S3 bucket is created
- Run simulator, trigger deliveries, check proofs appear in gallery via presigned URLs
- Toggle `PROOF_STORAGE=local` and confirm fallback works

---

## Phase 2: Twilio (SMS) + SendGrid (Email) Notifications

Wire real channels into the existing NotificationService stub.

### 2.1 Add dependencies and config
- **requirements.txt**: Add `twilio>=8.0.0`, `sendgrid>=6.9.0`
- **src/backend/core/config.py**: Add settings:
  - `NOTIFICATIONS_ENABLED: bool` (env toggle, default False)
  - `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER`
  - `SENDGRID_API_KEY`, `SENDGRID_FROM_EMAIL`
- **docker-compose.yml**: Add placeholder env vars to backend (empty by default)

### 2.2 Implement notification channels
- **MODIFY: src/backend/services/notifications.py**:
  - Add `_send_email(to_email, subject, body)` method using SendGrid `Mail` + `SendGridAPIClient`
  - Add `_send_sms(to_phone, body)` method using Twilio `Client.messages.create()`
  - Update `send_notification()`:
    - If `NOTIFICATIONS_ENABLED` is False, log-only (current behavior)
    - If enabled, determine channel from `contact_info` format: email address → email, phone number → SMS
    - Call appropriate `_send_email()` or `_send_sms()`
    - Wrap in try/except with logging on failure (no crash on send errors)
  - Add `_build_email_subject(event)` and `_build_email_html(event, message)` for templated emails

### 2.3 Update delivery route trigger
- **src/backend/api/routes/delivery.py**: At the `POST /confirm` notification trigger (line 147-152):
  - Keep BackgroundTasks pattern (already async)
  - No change needed to the call signature — just improve recipient/contact_info values
  - Add a comment noting that real recipient lookup would come from a customer DB table

### 2.4 Verification
- With `NOTIFICATIONS_ENABLED=false` (default): confirm no behavior change, logs only
- With real API keys: send a test delivery confirmation email/SMS and verify receipt
- Confirm errors in notification sending don't crash the delivery endpoint

---

## Phase 3: Redis for Heartbeats, Caching, and Pub/Sub

Replace the in-memory `driver_heartbeats` dict with Redis. Add Redis as a Docker service.

### 3.1 Add dependencies and config
- **requirements.txt**: Add `redis>=5.0.0`
- **src/backend/core/config.py**: Add:
  - `REDIS_URL: str = os.getenv("REDIS_URL", "")` — empty string means disabled/fallback to in-memory
- **docker-compose.yml**: Add `redis` service (redis:7-alpine, port 6379), add `REDIS_URL=redis://redis:6379/0` to backend env

### 3.2 Create Redis client module
- **NEW: src/backend/core/redis_client.py**:
  - `get_redis() -> redis.asyncio.Redis | None` — returns async Redis client or None if REDIS_URL empty
  - Lazy initialization with connection pooling
  - `redis_available() -> bool` helper

### 3.3 Create heartbeat service
- **NEW: src/backend/services/heartbeat.py**:
  - `HeartbeatService` class with two backends:
    - Redis mode: `SETEX driver:{driver_id}:heartbeat {timestamp} EX 60` (auto-expires)
    - Fallback mode: uses existing in-memory dict
  - Methods:
    - `async update(driver_id: str)` — SET with 60s TTL (Redis) or dict set (memory)
    - `async is_online(driver_id: str) -> bool` — EXISTS check (Redis) or dict check (memory)
    - `async get_online_count() -> int` — count keys matching `driver:*:heartbeat` (Redis) or dict length (memory)
    - `async get_last_heartbeat(driver_id: str) -> float | None` — GET (Redis) or dict get (memory)
  - Singleton `heartbeat_service = HeartbeatService()`

### 3.4 Migrate all heartbeat usages
Replace every `driver_heartbeats[driver_id] = time.time()` and `driver_heartbeats.get(driver_id)` across:
- **src/backend/api/routes/delivery.py** (lines 90, 125, 165): `await heartbeat_service.update(driver_id)`
- **src/backend/api/routes/tracking.py** (line 77): `await heartbeat_service.update(driver_id)`
- **src/backend/api/routes/tracking.py** (line 39-40): `is_online = await heartbeat_service.is_online(d.id)`
- **src/backend/api/routes/dispatch.py** (lines 78-79): `is_online = await heartbeat_service.is_online(d.id)`
- **src/backend/api/routes/dispatch.py** (line 182): `online_drivers = await heartbeat_service.get_online_count()`
- **src/backend/api/main.py** (lines 56-65): `active_count = await heartbeat_service.get_online_count()`
- **src/backend/api/metrics.py**: Keep `driver_heartbeats` dict for the fallback path but it's no longer the primary store

### 3.5 Verification
- `docker compose up -d` — Redis container starts
- Run simulator, verify drivers show online in dashboard
- Stop Redis container, verify fallback to in-memory works
- Check Prometheus `connected_drivers_total` still updates

---

## Phase 4: Mapbox Directions & Geocoding

Enhance routing and ETA with real road-network data from Mapbox APIs.

### 4.1 Add dependencies and config
- **requirements.txt**: Add `httpx>=0.27.0` (async HTTP client for Mapbox API calls)
- **src/backend/core/config.py**: Add:
  - `MAPBOX_ACCESS_TOKEN: str = os.getenv("MAPBOX_ACCESS_TOKEN", "")`
  - Empty token = disabled, falls back to current haversine/ML behavior

### 4.2 Create Mapbox service
- **NEW: src/backend/services/mapbox.py**:
  - `MapboxService` class with httpx.AsyncClient
  - `async get_directions(origin: tuple, destination: tuple) -> dict` — calls Mapbox Directions API, returns distance_km, duration_minutes, geometry
  - `async get_distance_matrix(origins: list, destinations: list) -> list` — calls Mapbox Matrix API for multi-stop optimization
  - `async geocode(address: str) -> tuple[float, float]` — forward geocoding
  - `async reverse_geocode(lat: float, lon: float) -> str` — reverse geocoding
  - All methods return None/fallback when token is empty
  - Singleton `mapbox_service = MapboxService()`

### 4.3 Enhance route optimization
- **src/backend/services/routing.py**:
  - Add `async optimize_route_mapbox(start, stops)` method that uses Mapbox Matrix API for real travel-time distances instead of haversine
  - Keep existing `optimize_route()` as fallback
- **src/backend/api/routes/routing.py**:
  - If Mapbox enabled: use real travel-time matrix for optimization, return Mapbox route geometries
  - If disabled: existing 2-Opt + haversine (no change)

### 4.4 Enhance ETA prediction
- **src/backend/api/routes/analytics.py**:
  - In `POST /predict-eta`: if Mapbox enabled, also fetch Mapbox Directions API duration
  - Return both ML estimate and Mapbox estimate; use weighted blend (e.g. 60% Mapbox, 40% ML) as final ETA
  - If Mapbox disabled: existing ML-only prediction (no change)

### 4.5 Add geocoding endpoint
- **src/backend/api/routes/routing.py**: Add two new endpoints:
  - `POST /route/geocode` — forward geocode an address string to lat/lon
  - `POST /route/reverse-geocode` — lat/lon to address string
  - Both return 501 if Mapbox token not configured

### 4.6 Verification
- With empty `MAPBOX_ACCESS_TOKEN`: confirm all existing behavior unchanged
- With valid token: test `/route/optimize` returns real road-network routes
- Test `/analytics/predict-eta` returns blended Mapbox+ML ETA
- Test geocoding endpoints with sample addresses

---

## Summary of New/Modified Files

| File | Action | Phase |
|------|--------|-------|
| requirements.txt | Modify (add boto3, twilio, sendgrid, redis, httpx) | 1-4 |
| src/backend/core/config.py | Modify (add all config vars) | 1-4 |
| docker-compose.yml | Modify (add localstack, redis services + env vars) | 1, 3 |
| src/backend/services/storage.py | **New** | 1 |
| src/backend/api/routes/delivery.py | Modify | 1, 2, 3 |
| src/web/src/api/delivery.ts | Modify | 1 |
| src/backend/services/notifications.py | Modify | 2 |
| src/backend/core/redis_client.py | **New** | 3 |
| src/backend/services/heartbeat.py | **New** | 3 |
| src/backend/api/routes/tracking.py | Modify | 3 |
| src/backend/api/routes/dispatch.py | Modify | 3 |
| src/backend/api/main.py | Modify | 3 |
| src/backend/services/mapbox.py | **New** | 4 |
| src/backend/services/routing.py | Modify | 4 |
| src/backend/api/routes/routing.py | Modify | 4 |
| src/backend/api/routes/analytics.py | Modify | 4 |
