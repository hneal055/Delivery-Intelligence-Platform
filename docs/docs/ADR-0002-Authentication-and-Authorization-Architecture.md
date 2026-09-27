ADR-0002: Authentication and Authorization Architecture

Status: Accepted

Date: 2026-09-26

Authors: Chicago Cargo Courier LLC

Decision Type: Security Architecture Decision

Supersedes: None

Related ADRs:

ADR-0001 Platform Architecture
Context

The Delivery Intelligence Platform (DIP) requires a secure authentication and authorization model capable of supporting:

Dispatcher dashboards
Driver mobile applications
Administrative operations
API integrations
Future third-party system integrations

The platform manages operationally sensitive logistics data including:

Driver locations
Customer destinations
Delivery confirmations
Proof-of-delivery evidence
Fleet telemetry
Route intelligence

Access must therefore be controlled through a centralized, auditable, role-based security model.

Decision

The platform will use:

Authentication
OAuth2 Password Flow
JWT Access Tokens


Authorization
Role-Based Access Control (RBAC)
using dependency-injected authorization policies at the API layer.

Password Storage

Passwords will never be stored in plaintext.

All passwords are stored using:
bcrypt hashing
before persistence to PostgreSQL.


Authentication Flow
Login

User submits credentials:
POST /auth/token


Example:
{
  "username": "admin",
  "password": "********"
}

Validation

Authentication service performs:
Username lookup
Password hash verification
Account status validation
Role retrieval

Token Issuance

If authentication succeeds:
{
  "access_token": "JWT",
  "token_type": "bearer"
}
is returned.


Protected API Access

Client sends:
Authorization: Bearer <JWT>

header with every protected request.

Request Authorization

JWT is validated through FastAPI dependencies.

Authorization policies evaluate:
User identity
Account status
Assigned role
Endpoint permissions

before request execution.


Security Model
Identity Types

The platform currently supports:

Identity Type	PurposeAdmin	Full platform administration
Dispatcher	Dispatch operations
Driver	Mobile delivery operations
Role Definitions
Admin

Capabilities:
User administration
Dispatch operations
Fleet visibility
Analytics access
System management

Status:

✅ Implemented

Dispatcher

Capabilities:
Job assignment
Routing operations
Dispatch management
Driver monitoring
Delivery oversight

Status:

✅ Implemented


Driver

Capabilities:
Route execution
Location reporting
Proof-of-delivery submission
Equipment scanning
Delivery status updates

Status:

✅ Implemented



Current Authentication Architecture
User
  │
  ▼

POST /auth/token
  │
  ▼

Authentication Service
  │
  ▼

PostgreSQL Users Table
  │
  ▼

Password Hash Verification
  │
  ▼

JWT Generation
  │
  ▼

Bearer Token Returned
  │
  ▼

Protected Endpoint Access


Database Design
Users Table

Authentication depends upon:
users

table.

Current validated fields:
id
username
email
hashed_password
role
is_active
created_at

Status:

✅ Operational


JWT Architecture
Token Type
Bearer Token


Signing Algorithm

Current implementation:
HS256


JWT Contains
User Identifier
Username
Role
Expiration Timestamp

Current status:

✅ Operational

FastAPI Security Model

FastAPI dependency injection is used to enforce security.

Example authorization layers:
get_current_user()

get_current_active_user()

require_admin()

require_dispatcher()



Benefits
Centralized Security

All routes use the same authentication mechanism.

Consistent Authorization

Authorization rules remain reusable and testable.

Reduced Duplication

Security logic is maintained in one location.

Current Validated Security Components
Operational
Component	StatusPostgreSQL User Store	✅
Password Hashing	✅
Authentication Endpoint	✅
JWT Issuance	✅
OAuth2 Password Flow	✅
Swagger Authentication	✅
Role Storage	✅
User Seeding	✅
Validation Evidence

Successfully validated:
POST /auth/token

Result:
200 OK

JWT token successfully returned.

Status:

✅ Verified

Seeded Security Accounts

The platform currently initializes:
admin
dispatcher1
driver1
driver2
driver3

through:
python -m tools.seed_db

Status:

✅ Validated


Security Controls
Password Protection

Passwords are:
Hashed
Never stored in plaintext
Never returned via API

Status:

✅ Operational



API Protection

Protected endpoints require:
Authorization: Bearer <token>

Status:

✅ Operational

Role Enforcement

RBAC permissions are enforced at the API layer.

Status:

✅ Operational


Audit Logging

Authentication events and user actions may be recorded within:
audit_logs


for future compliance and operational review.

Status:

🔄 Validation Pending


Threat Model
Unauthorized Access

Mitigated by:

JWT Authentication
Role Enforcement
Password Hashing


Credential Theft

Mitigated by:
bcrypt
HTTPS/TLS (production)
Short-lived tokens


Privilege Escalation

Mitigated by:
Role Validation
Dependency-Based Authorization
RBAC Enforcement


Current Risks
Dispatch Dashboard Authorization

Status:

🔄 Active Investigation

Endpoint:
GET /dispatch/dispatch/dashboard/summary

Observed response:
{
  "detail": "Not authenticated"
}

Potential causes:

JWT propagation
Swagger authorization integration
Router-level authorization dependency
OAuth configuration mismatch


Future Security Decisions

Planned enhancements:

Refresh Tokens

Future support for:
JWT Refresh Tokens

Status:

⬜ Planned


External Identity Providers

Future support for:
Microsoft Entra ID
Google
OIDC Providers

Status:

⬜ Planned

Multi-Factor Authentication

Future support for:

MFA
TOTP
Push Authentication

Status:

⬜ Planned


Secrets Management

Migration from:
.env

to:
Docker Secrets
Vault
Cloud Secret Stores

Status:

⬜ Planned



Consequences
Positive Outcomes
Simplicity

FastAPI OAuth2 implementation is simple and maintainable.

Security

bcrypt and JWT provide strong foundational security.

Scalability

Architecture can support:

Mobile applications
Web applications
API integrations
Future external identity providers
Operational Visibility

Authentication can be audited and monitored centrally.

Tradeoffs
Token Management

JWT introduces token lifecycle management requirements.

Future Integration Work

External identity providers will require additional implementation effort.

Decision Outcome

The Delivery Intelligence Platform will use:
OAuth2 Password Flow
+ JWT Bearer Tokens
+ Role-Based Access Control
+ bcrypt Password Hashing

as the foundational authentication and authorization architecture.

Current maturity:
Authentication Service        ✅ Operational
JWT Issuance                  ✅ Operational
RBAC Enforcement              ✅ Operational
Swagger Authentication        ✅ Operational
Dispatch Authorization        🔄 Validation In Progress
External Identity Providers   ⬜ Planned
MFA                           ⬜ Planned

Decision Status: Accepted ✅

Review Trigger: Completion of Phase 5 Functional Validation or implementation of external identity providers.
















