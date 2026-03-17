# Delivery Intelligence Platform — Architecture

## System Architecture Diagram

```mermaid
graph TB
    subgraph Clients["Client Layer"]
        Browser["Browser\n(Dispatcher Dashboard)"]
        Mobile["Mobile App\n(Driver App)"]
        External["External Systems\n(Webhooks / API)"]
    end

    subgraph Gateway["Ingress Layer"]
        Nginx["Nginx / k8s Ingress\n(TLS termination, rate limit)"]
    end

    subgraph API["API Layer — FastAPI (Python 3.12)"]
        Auth["Auth Routes\n/auth/*"]
        Delivery["Delivery Routes\n/delivery/*"]
        Dispatch["Dispatch Routes\n/dispatch/*"]
        Tracking["Tracking Routes\n/tracking/*"]
        Routing["Routing Routes\n/routing/*\n(haversine + Mapbox)"]
        Analytics["Analytics Routes\n/analytics/*\n(ETA ML, geofencing)"]
        AdvRouting["Advanced Routing\n/routing/advanced/*\n(time windows, vehicle profiles)"]
        WS["WebSocket Routes\n/ws/dispatcher\n/ws/driver"]
        Middleware["OTel Tracing\nSlowAPI Rate Limiting\nJWT Auth Middleware"]
    end

    subgraph Workers["Background Workers — ARQ"]
        ARQWorker["ARQ Worker\n(async task queue)"]
        Heartbeat["Heartbeat Service\n(driver location pings)"]
        Notifications["Notifications Service\n(SMS via Twilio, email)"]
    end

    subgraph Data["Data Layer"]
        PG[("PostgreSQL 15\n+ PostGIS 3.3\n\nDeliveries, Packages\nDrivers, Dispatchers\nTime Windows\nVehicle Profiles")]
        Redis[("Redis 7\n\nPub/Sub broadcast\nRate limit counters\nSession cache")]
        S3["S3 / LocalStack\n(Proof-of-delivery\nimage storage)"]
    end

    subgraph RedisMgr["Redis Pub/Sub Manager"]
        PubSub["RedisPubSubManager\n(auto-reconnect loop)\nBroadcast to dispatchers\nUnicast to drivers"]
    end

    subgraph Ext["External Services"]
        Mapbox["Mapbox API\n(directions matrix\ngeocoding)"]
        Twilio["Twilio / SMTP\n(SMS + email)"]
    end

    subgraph Observability["Observability Stack"]
        Prometheus["Prometheus\n:9090"]
        Grafana["Grafana\n:3001\n(10 dashboards)"]
        Alertmanager["Alertmanager\n:9093\n(PagerDuty / Slack)"]
        PGExporter["postgres_exporter"]
        RedisExporter["redis_exporter"]
        OTEL["OpenTelemetry SDK\n(traces → Jaeger / OTLP)"]
    end

    subgraph CI["CI/CD — GitHub Actions"]
        Tests["pytest\n237 tests · 80% cov"]
        HelmLint["helm lint\n(default + staging + prod)"]
        Build["docker build + push\nGHCR (cosign signed)"]
        Staging["deploy-staging\n(smoke test × 12)"]
        LoadTest["Locust load test\n30 users · SLO enforced"]
        Migrate["alembic upgrade head\n(prod — gated by staging)"]
        Helm["helm upgrade\n(prod)"]
    end

    %% Client → Gateway → API
    Browser --> Nginx
    Mobile --> Nginx
    External --> Nginx
    Nginx --> Auth & Delivery & Dispatch & Tracking & Routing & Analytics & AdvRouting & WS

    %% API → Data
    Auth & Delivery & Dispatch & Tracking & Routing & Analytics & AdvRouting --> PG
    Delivery --> S3
    WS --> PubSub

    %% Pub/Sub → Redis
    PubSub --> Redis
    PubSub -.->|"fan-out\nmessages"| WS

    %% API → Workers
    Delivery & Dispatch & Notifications --> ARQWorker
    ARQWorker --> Redis
    ARQWorker --> Heartbeat & Notifications

    %% External
    Routing --> Mapbox
    Notifications --> Twilio

    %% Observability wiring
    API --> OTEL
    PG --> PGExporter --> Prometheus
    Redis --> RedisExporter --> Prometheus
    Prometheus --> Grafana
    Prometheus --> Alertmanager

    %% CI/CD pipeline order
    Tests --> HelmLint --> Build --> Staging --> LoadTest
    Staging --> Migrate --> Helm
```

---

## Component Inventory

| Component | Technology | Port | Notes |
|---|---|---|---|
| API Backend | FastAPI + Uvicorn | 8002 | Async, OTel-instrumented |
| Database | PostgreSQL 15 + PostGIS 3.3 | 5434 | Geospatial queries, Alembic migrations |
| Cache / PubSub | Redis 7 | 6379 | Pub/Sub for WebSocket fan-out; rate limiting |
| Background Workers | ARQ (asyncio task queue) | — | Delivery events, heartbeat, notifications |
| Proof Storage | S3 / LocalStack (dev) | 4566 | SHA-keyed images, pre-signed URLs |
| Routing Engine | Mapbox API + haversine 2-Opt | — | Falls back to haversine when no token |
| ML / Analytics | scikit-learn ETAPredictor | — | Trained model persisted to disk |
| Geofencing | Shapely + PostGIS | — | Circular zones + polygon containment |
| Metrics | Prometheus + postgres/redis exporters | 9090 | Scraped every 15 s |
| Dashboards | Grafana | 3001 | 10 pre-built panels |
| Alerting | Alertmanager | 9093 | PagerDuty + Slack receivers |
| Tracing | OpenTelemetry SDK | — | OTLP export (disabled in tests) |
| Object Store (dev) | LocalStack | 4566 | Emulates S3, SQS, SNS |

---

## Data Flow: Proof-of-Delivery Upload

```mermaid
sequenceDiagram
    participant Driver as Driver App
    participant API as FastAPI Backend
    participant DB as PostgreSQL
    participant S3 as S3 / LocalStack
    participant Dispatcher as Dispatcher Dashboard

    Driver->>API: POST /delivery/{id}/proof (multipart image)
    API->>API: Validate JWT + RBAC (driver role)
    API->>S3: upload(key=PKG-{id}-{ts}.jpg, data)
    S3-->>API: storage key
    API->>DB: UPDATE delivery SET proof_url=key, status=delivered
    DB-->>API: updated record
    API->>API: RedisPubSubManager.broadcast_to_dispatchers()
    API-->>Driver: 200 { proof_url }
    API->>Dispatcher: WebSocket push { event: proof_uploaded, delivery_id }
```

---

## Data Flow: Real-Time Driver Tracking

```mermaid
sequenceDiagram
    participant Driver as Driver App
    participant API as FastAPI Backend
    participant Redis as Redis Pub/Sub
    participant Worker as ARQ Worker
    participant Dispatcher as Dispatcher Dashboard

    Driver->>API: WebSocket /ws/driver/{driver_id}
    API->>Redis: SUBSCRIBE delivery_platform_broadcast
    loop Every 5 s
        Driver->>API: { lat, lon, timestamp }
        API->>Worker: enqueue heartbeat_task(driver_id, location)
        Worker->>Redis: PUBLISH broadcast { driver_id, lat, lon }
        Redis-->>API: message delivered
        API->>Dispatcher: WebSocket push { driver_id, location }
    end
```

---

## CI/CD Pipeline

```mermaid
graph LR
    Push["git push main"] --> Test["test\n(pytest 237 tests)"]
    Test --> Lint["helm-lint\n(3 value sets)"]
    Lint --> Build["build-push\nGHCR + cosign sign"]
    Build --> Staging["deploy-staging\n(k8s staging env)"]
    Staging --> LoadTest["load-test\nLocust 30 users 2 min\nSLO: p95 < 500 ms"]
    Staging --> Migrate["alembic migrate\n(prod — hard gate)"]
    Migrate --> Deploy["helm upgrade\n(prod)"]
```

---

## Security Controls

| Layer | Control |
|---|---|
| Transport | TLS via cert-manager (Let's Encrypt) |
| Authentication | JWT (HS256), bcrypt password hashing |
| Authorization | RBAC (admin / dispatcher / driver) via FastAPI deps |
| Rate Limiting | SlowAPI (per-IP, per-endpoint limits) |
| Input Validation | Pydantic v2 strict schemas on all endpoints |
| Secrets | `.env` file (never committed); Docker secrets in production |
| Dependencies | pip-compile with SHA-256 hashes (`--require-hashes`) |
| Images | Cosign-signed GHCR images; non-root container user |
| Storage | LocalStorage blocked in production; S3 enforced |
| Monitoring | Alertmanager → PagerDuty on error rate / latency SLO breach |
