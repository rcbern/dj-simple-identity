# Directory Structure

> **Section 4** of the Auth Microservice Architecture Specification. See [`README.md`](README.md) for the full index.

```text
auth_service/                     # Django Project Root
├── certs/                        # JWT RS256 Asymmetric Keys
│   ├── private.pem               # Used ONLY by Auth service to sign tokens
│   └── public.pem                # Shared with FastAPI Gateway to verify tokens
├── auth/                         # The single Auth Django App
│   ├── models/                   # Database Schema (Lean, modular)
│   │   ├── user.py               # Custom User model (No PermissionsMixin)
│   │   ├── token.py              # Unified Token model (Rotation, Reuse, Attempts)
│   │   ├── mfa.py                # UserMFA model (TOTP, OneToOne)
│   │   └── sso.py                # SocialAccount model
│   ├── services/                 # Internal Business Logic
│   │   ├── token_service.py      # RS256 signing, Hashing, Rotation, Reuse Detection
│   │   ├── auth_service.py       # Login, Logout, Refresh, Cookie logic
│   │   ├── account_service.py    # Register, Verify Email, Reset Password
│   │   ├── mfa_service.py        # TOTP enrollment, Fernet encryption
│   │   └── sso_service.py        # SSO logic with Email Collision Protection
│   ├── infrastructure/           # Cross-cutting concerns
│   │   └── event_publisher.py    # Pushes domain events to Redis Streams
│   ├── integrations/             # External API Adapters (ABCs)
│   │   └── sso/
│   │       ├── base.py           # AbstractSSOService
│   │       └── github.py         # GitHubSSOService
│   ├── api/                      # Django Ninja REST Layer
│   │   ├── auth.py               # JWTAuth Dependency (Protects internal routes)
│   │   ├── middleware.py         # RequestID Middleware
│   │   ├── schemas/              # Pydantic Data Transfer Objects
│   │   └── routers/              # Endpoint Controllers (Thin)
│   └── tests/                    # Test Suite
└── auth_service/                 # Django Project Settings
```

## Related documents
- [Overview](overview.md)
- [Architectural Decisions Summary](architectural-decisions.md)
- [Identity & Users](domains/identity-and-users.md)
- [Token Management & Security](domains/token-management.md)
- [Authentication & Sessions](domains/authentication-and-sessions.md)
- [Account Lifecycle & Events](domains/account-lifecycle.md)
- [Multi-Factor Authentication (MFA)](domains/mfa.md)
- [Single Sign-On (SSO)](domains/sso.md)
- [REST API (Django Ninja)](api/rest-api.md)
- [Logging and Observability](observability.md)