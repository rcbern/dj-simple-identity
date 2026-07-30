# Directory Structure

> **Section 4** of the Auth Microservice Architecture Specification. See [`README.md`](README.md) for the full index.

```text
auth_service/                     # Django Project Root
├── certs/                        # JWT RS256 Asymmetric Keys
│   ├── private.pem               # Used ONLY by Auth service to sign tokens
│   └── public.pem                # Shared with FastAPI Gateway to verify tokens
├── config/                       # Django Project Settings
│   ├── __init__.py
│   ├── settings.py               # Environment-driven settings (django-environ)
│   ├── urls.py                   # URL routing — mounts NinjaAPI at /api/
│   ├── asgi.py
│   └── wsgi.py
├── identity/                     # The single Auth Django App
│   ├── __init__.py
│   ├── apps.py
│   ├── admin.py
│   ├── exceptions.py             # Custom domain exception hierarchy
│   ├── models/                   # Database Schema (Lean, modular)
│   │   ├── __init__.py
│   │   ├── user.py               # Custom User model (No PermissionsMixin)
│   │   ├── token.py              # Lean Token model (no session families)
│   │   ├── mfa.py                # UserMFA model (TOTP, OneToOne)
│   │   └── sso.py                # SocialAccount model
│   ├── services/                 # Internal Business Logic
│   │   ├── __init__.py
│   │   ├── token_service.py      # RS256 signing, Hashing, Issue/Decode
│   │   ├── auth_service.py       # Login, Logout, Refresh, Access Token
│   │   ├── account_service.py    # Register, Verify Email, Reset Password
│   │   ├── mfa_service.py        # TOTP enrollment, Fernet encryption
│   │   └── sso_service.py        # SSO logic with Email Collision Protection
│   ├── infrastructure/           # Cross-cutting concerns
│   │   ├── __init__.py
│   │   └── event_publisher.py    # Pushes domain events to Redis Streams
│   ├── integrations/             # External API Adapters (ABCs)
│   │   ├── __init__.py
│   │   └── sso/
│   │       ├── __init__.py       # Factory pattern (get_sso_service)
│   │       ├── base.py           # AbstractSSOService
│   │       └── github.py         # GitHubSSOService
│   ├── api/                      # Django Ninja REST Layer
│   │   ├── __init__.py
│   │   ├── auth.py               # JWTAuth Dependency (Protects internal routes)
│   │   ├── middleware.py         # RequestID Middleware
│   │   ├── schemas/              # Pydantic Data Transfer Objects
│   │   │   ├── __init__.py
│   │   │   ├── common.py         # Error, Message, TokenPair, MFAChallenge
│   │   │   └── requests.py       # Request payload schemas per domain
│   │   └── routers/              # Endpoint Controllers (Thin)
│   │       ├── __init__.py       # NinjaAPI instance + router registration
│   │       ├── auth.py           # Login, MFA verify, Refresh, Logout
│   │       ├── account.py        # Register, Verify, Password reset, Change
│   │       ├── mfa.py            # Enroll, Verify/Enable
│   │       └── sso.py            # SSO callback
│   ├── migrations/
│   │   ├── __init__.py
│   │   └── 0001_initial.py
│   └── tests/                    # (Reserved for future app-level tests)
├── tests/                        # Project-level test suite
│   ├── __init__.py
│   ├── conftest.py               # fakeredis + Fernet key fixtures
│   ├── factories.py              # Factory Boy factories
│   ├── test_services.py          # Service-layer unit tests
│   ├── test_infrastructure.py    # EventPublisher tests
│   └── test_api.py               # API integration tests (NinjaAPI TestClient)
├── scripts/
│   └── generate_keys.py          # Generate RS256 key pair + Fernet key
├── pyproject.toml                # Dependencies, ruff, ty, pytest config
├── uv.lock                       # Locked dependencies
└── manage.py
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