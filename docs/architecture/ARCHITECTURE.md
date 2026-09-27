ADR-0001: Delivery Intelligence Platform Architecture

Status: Accepted

Date: 2026-09-26

Authors: Chicago Cargo Courier LLC

Decision Type: Foundational Architecture Decision

Context

The Delivery Intelligence Platform (DIP) is being developed as a modular logistics intelligence platform supporting:

Dispatch Operations
Fleet Management
Driver Tracking
Proof of Delivery (POD)
Route Optimization
Geospatial Intelligence
Predictive Analytics
Operational Command Center Functions

The platform must support:

Real-time operational data
Geospatial processing
Mobile driver workflows
API-first integrations
Future cloud-native deployment
High observability
Machine-learning enhancements

The platform must also support growth from a development and validation environment into production-scale operations.

Decision

The Delivery Intelligence Platform will adopt a layered, service-oriented architecture built around:

Plain Text
Client Layer
↓
API Layer
↓
Data Services
↓
Background Processing
↓
External Services
↓
Observability Layer
Show more lines

The platform will initially be deployed using Docker Compose and evolve toward Kubernetes-based deployment in future phases.

Architecture Decision Summary
Domain	DecisionAPI Framework	FastAPI
Programming Language	Python 3.12
Database	PostgreSQL 15
Geospatial Engine	PostGIS
Authentication	OAuth2 + JWT
Cache / PubSub	Redis
Background Processing	ARQ
Object Storage	S3 Compatible Storage
Telemetry	OpenTelemetry
Metrics	Prometheus
Visualization	Grafana
Routing	Mapbox + Haversine Fallback
ML Framework	Scikit-Learn
Deployment	Docker Compose (Current)
Future Deployment	Kubernetes + Helm
Current Validated Architecture

The following components have been verified operational during platform recovery.

Infrastructure
Component	StatusDocker Environment	✅ Operational
FastAPI Backend	✅ Operational
PostgreSQL	✅ Operational
PostGIS	✅ Operational
Redis	✅ Operational
Database Layer

The following schema components have been successfully migrated and validated:

Plain Text
users
drivers
packages
dispatch_jobs
audit_logs
device_tokens
location_history
route_history
vehicle_profiles
time_window_constraints
Show more lines

Status:

✅ Operational

Security Layer
Component	StatusOAuth2 Authentication	✅
JWT Token Generation	✅
RBAC Authorization	✅
Pydantic Validation	✅
Audit Logging Framework	✅
API Layer
Service	StatusAuthentication APIs	✅
User APIs	✅
Dispatch APIs	🔄
Tracking APIs	⬜
Routing APIs	⬜
Analytics APIs	⬜
Logical Architecture
Plain Text
Clients
│
▼
Nginx / Ingress
│
▼
FastAPI API Layer
│
┌──┴──────────────┐
▼ ▼
Redis PostgreSQL
Pub/Sub PostGIS
│
▼
Background Workers
│
▼
Notification Services
│
▼
External Providers
Show more lines
Component Responsibilities
Client Layer
Dispatcher Dashboard

Responsibilities:

Dispatch management
Fleet monitoring
Delivery oversight
Operational reporting
Driver Mobile Application

Responsibilities:

Route execution
Navigation
Proof-of-delivery submission
Equipment scanning
Driver telemetry
External Integrations

Responsibilities:

API integrations
Webhooks
Partner communications
API Layer
Authentication Service

Responsibilities:

User authentication
Token issuance
Token validation
Role verification

Status:

✅ Operational

Dispatch Service

Responsibilities:

Driver assignment
Job management
Delivery coordination
Dispatch workflows

Status:

🔄 Validation In Progress

Tracking Service

Responsibilities:

Location updates
GPS telemetry
Route playback
Driver monitoring

Status:

⬜ Pending Validation

Routing Service

Responsibilities:

Route generation
Geocoding
ETA calculations
Route optimization

Status:

⬜ Pending Validation

Analytics Service

Responsibilities:

ETA prediction
Performance analysis
Driver insights
Operational reporting

Status:

⬜ Pending Validation

Data Layer
PostgreSQL

Chosen because:

ACID compliance
Proven scalability
Mature ecosystem
SQLAlchemy compatibility
PostGIS

Chosen because:

Native geospatial indexing
Geofence support
Spatial optimization
GIS compatibility
Redis

Chosen because:

Low-latency pub/sub
WebSocket broadcasting
Session caching
Future queue support
Background Processing
ARQ Workers

Responsibilities:

Heartbeat processing
Notification delivery
Async delivery workflows
Deferred analytics tasks

Status:

🔄 Not Fully Validated

Object Storage
S3-Compatible Storage

Responsibilities:

POD image storage
Signature storage
File retention
Evidence management

Development Environment:
LocalStack

Production Target:
AWS S3 Compatible Storage

External Integrations
Mapbox

Responsibilities:

Route generation
Geocoding
Reverse geocoding
Traffic intelligence

Status:

⬜ Validation Pending

Twilio

Responsibilities:

SMS notifications
Driver alerts
Dispatch notifications

Status:

⬜ Validation Pending

Observability Strategy
Current State
Logging

✅ Application logs

✅ Docker logs

✅ Database logs

Target State
Metrics
Prometheus
Exporters
Service metrics
Dashboards
Grafana
Fleet dashboards
Dispatch dashboards
Tracing
OpenTelemetry
OTLP Export
Alerting
Alertmanager
Slack
PagerDuty

Status:

⬜ Planned

Deployment Strategy
Current Deployment

Platform deployment is performed manually.

Build
docker compose build

Startup
docker compose up -d

Migration
alembic upgrade head


Seed
python -m tools.seed_db


Status:

✅ Operational

Future Deployment Strategy

Target deployment architecture:
GitHub Actions
     ↓
Automated Testing
     ↓
Container Build
     ↓
Security Validation
     ↓
Staging Deployment
     ↓
Load Testing
     ↓
Production Deployment

Target technologies:

GitHub Actions
Helm
Kubernetes
Cosign
Prometheus
Alertmanager

Status:

⬜ Planned

Consequences
Positive
Scalability

Modular services support future growth.

Observability

Architecture supports modern monitoring and tracing.

Security

OAuth2, JWT, RBAC, and audit logging provide strong security foundations.

Geospatial Processing

PostGIS provides enterprise-grade location intelligence.

Extensibility

Architecture supports:

Mobile applications
Third-party integrations
ML pipelines
Future microservices
Tradeoffs
Increased Complexity

Docker, PostgreSQL, Redis, and background workers increase operational complexity.

Additional Infrastructure

Observability stack introduces more infrastructure to manage.

Validation Requirements

Several future-state components remain unvalidated and require phased implementation.

Risks
Dispatch Dashboard Authorization

Status:

🔄 Active Investigation

Observed:
{
  "detail": "Not authenticated"
}

Potential Causes:

JWT propagation
Swagger authorization handling
Router dependency configuration


Future Decisions

Expected future ADRs:
ADR-0002 Authentication & Security Model
ADR-0003 Dispatch Workflow Architecture
ADR-0004 Geospatial Routing Architecture
ADR-0005 Analytics Platform Architecture
ADR-0006 Kubernetes Deployment Strategy
ADR-0007 Mobile Platform Architecture


Decision Outcome

The Delivery Intelligence Platform adopts a layered FastAPI + PostgreSQL/PostGIS + Redis architecture that has successfully completed infrastructure recovery, database restoration, schema migration, and authentication validation.

Current maturity:
Infrastructure Recovery      ✅ Complete
Database Recovery            ✅ Complete
Authentication Recovery      ✅ Complete
Dispatch Validation          🔄 In Progress
Tracking Validation          ⬜ Pending
Routing Validation           ⬜ Pending
Analytics Validation         ⬜ Pending
Production Hardening         ⬜ Pending


Decision Status: Accepted ✅

Review Date: After completion of Phase 5 Functional Validation.






