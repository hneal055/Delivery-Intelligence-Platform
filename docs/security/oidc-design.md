# OIDC Design

## Goal

Introduce Microsoft Entra ID authentication without impacting the existing local authentication system.

## Existing Authentication

Current:

POST /auth/token

Uses:

- OAuth2PasswordBearer
- bcrypt
- JWT (HS256)

## Target Authentication

### Local Login

POST /auth/token

Remains supported.

### Enterprise Login

GET /oidc/login

Redirects to Microsoft Entra ID.

### Callback

GET /oidc/callback

Processes Entra ID token.

### Claims

Required:

- sub
- email
- preferred_username

Optional:

- groups
- roles

## Migration Strategy

Phase 1

- OIDC endpoints only
- No authentication changes

Phase 2

- OIDC token validation

Phase 3

- Group-to-role mapping

Phase 4

- MFA enforcement

Phase 5

- Disable local accounts if desired