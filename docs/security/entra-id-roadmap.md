# Microsoft Entra ID Roadmap

## Objective

Modernize authentication and identity management by adding Microsoft Entra ID (OIDC) while preserving the existing username/password authentication system.

The migration will be performed in phases with zero disruption to current users.

---

# Current State Assessment

## Authentication

Current implementation:

- FastAPI OAuth2PasswordBearer
- Username/password authentication
- bcrypt password hashing
- JWT access tokens
- HS256 signing algorithm
- Role-based access control (RBAC)

## Existing OIDC Readiness

Already present:

- OIDC_ENABLED
- OIDC_ISSUER_URL
- OIDC_CLIENT_ID
- authlib dependency

## Security Gaps

- No Microsoft Entra ID integration
- No enterprise SSO
- No MFA enforcement
- No SCIM provisioning
- HS256 shared-secret JWT model
- No enterprise federation

---

# Phase 1 - Discovery and Documentation

Status: Complete

Deliverables:

- Authentication architecture reviewed
- JWT implementation reviewed
- Password hashing reviewed
- RBAC implementation reviewed
- OIDC readiness reviewed

---

# Phase 2 - OIDC Foundation

## Goal

Introduce OIDC support without changing existing authentication.

### New Route Module

Create:

```text
src/backend/api/routes/oidc.py