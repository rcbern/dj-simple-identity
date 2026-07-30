# Overview

This microservice is the single source of truth for identity, authentication, and session management. It is designed around a "Fat Services, Lean Models" philosophy. Database models act as pure data containers, while all business logic is isolated in dedicated service classes.

It sits behind a FastAPI Gateway (which handles rate limiting, CORS, and stateless Access Token validation). The Auth service communicates asynchronously with the rest of the system via Redis Streams.

---

## Tech Stack

* **Framework:** Django 6.0+
* **REST API:** Django Ninja 1.6+ (Pydantic validation)
* **Database:** PostgreSQL (via `psycopg[binary]`)
* **Cache/Message Broker:** Redis 8.1+ (Redis Streams for Event-Driven Architecture)
* **Security Libraries:** `PyJWT` (RS256), `pyotp` (TOTP), `cryptography` (Fernet), `argon2-cffi` (password hashing), Python `secrets` & `hashlib`
* **Testing:** `pytest`, `pytest-django`, `pytest-mock`, `factory-boy`, `fakeredis`
* **Linting & Type Checking:** `ruff` (lint + format), `ty` (static type checking)
* **Logging:** `python-json-logger`
* **Package Management:** `uv` (Astral)

---

## Architectural Decisions

1. **Gateway-Ready Architecture:** The Auth service does not handle rate limiting, CORS, or internal gRPC token validation. A FastAPI Gateway sits in front, holding the JWT Public Key to validate Access Tokens locally before routing requests.
2. **Asymmetric JWTs (RS256):** The Auth service signs stateless Access Tokens with an RSA Private Key. The Gateway and other microservices verify them using the Public Key.
3. **Hybrid Opaque Refresh Tokens:** Refresh tokens are delivered to the client as JWTs wrapping an opaque string. The database stores a SHA-256 hash of that string.
4. **Simple Rotation (No Session Families):** On `/refresh`, the old token is deleted and a new one is issued. The implementation intentionally omits session-family tracking and reuse detection — brute-force protection is delegated to the gateway's rate limiter, and the lean `Token` model keeps the schema minimal.
5. **Event-Driven Notifications:** The Auth service **does not send emails**. It publishes events to Redis Streams.
6. **Dependency Inversion for SSO:** SSO integrations rely on Abstract Base Classes, allowing easy swapping of providers without touching business logic.
7. **Explicit `request_id` Logging:** Correlation IDs are passed explicitly through function arguments to `extra` in the logger, avoiding `contextvars`.
8. **Custom Domain Exceptions:** All services raise semantically meaningful custom exceptions (e.g. `InvalidCredentialsError`, `TokenInvalidError`, `SSOEmailCollisionError`) instead of bare `ValueError`/`PermissionError`, making API-layer error handling cleaner.

---

## Directory Structure

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

---

## Testing Strategy

### Overview
Testing relies on `pytest` and `pytest-django`. The test suite mirrors the strict separation of concerns. Services are tested with mocked integrations. API integration tests use the NinjaAPI `TestClient`.

### Dependencies
```text
pytest
pytest-django
pytest-mock
factory-boy
fakeredis
```

### Configuration (`pyproject.toml`)
```toml
[tool.pytest.ini_options]
DJANGO_SETTINGS_MODULE = "config.settings"
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
```

### Shared Fixtures (`tests/conftest.py`)
An autouse fixture patches Redis with `fakeredis` for all tests. A second autouse fixture ensures a valid Fernet key is set for MFA encryption.

```python
# tests/conftest.py
import fakeredis
import pytest
from cryptography.fernet import Fernet
from django.conf import settings
from unittest.mock import patch


@pytest.fixture(autouse=True)
def _fakeredis():
    fake_client = fakeredis.FakeRedis(decode_responses=True)
    with patch("identity.infrastructure.event_publisher.redis.Redis") as mock:
        mock.return_value = fake_client
        yield mock


@pytest.fixture(autouse=True)
def _fernet_key():
    if not hasattr(settings, "MFA_ENCRYPTION_KEY") or not settings.MFA_ENCRYPTION_KEY:
        settings.MFA_ENCRYPTION_KEY = Fernet.generate_key()
```

### Factories (`tests/factories.py`)
```python
# tests/factories.py
import factory
from cryptography.fernet import Fernet
from django.conf import settings

from identity.models.mfa import UserMFA
from identity.models.sso import SocialAccount
from identity.models.token import Token, TokenType
from identity.models.user import User


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    email = factory.Sequence(lambda n: f"user{n}@test.com")
    password = factory.PostGenerationMethodCall("set_password", "TestPass123!")
    is_active = True
    is_verified = True


class TokenFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Token

    user = factory.SubFactory(UserFactory)
    token_type = TokenType.REFRESH
    token_hash = factory.Sequence(lambda n: f"hash{n}" * 8)
    expires_at = factory.Faker("future_datetime")


class UserMFAFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = UserMFA

    user = factory.SubFactory(UserFactory)
    mfa_type = "TOTP"
    is_enabled = True

    @factory.lazy_attribute
    def secret(self) -> str:
        fernet = Fernet(settings.MFA_ENCRYPTION_KEY)
        return fernet.encrypt(b"JBSWY3DPEHPK3PXP").decode("utf-8")


class SocialAccountFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SocialAccount

    user = factory.SubFactory(UserFactory)
    provider = "GITHUB"
    provider_user_id = factory.Sequence(lambda n: str(n))
    provider_email = factory.SelfAttribute("user.email")
```

### Test Example: Service Tests (`tests/test_services.py`)
Service tests use `TestCase` and factory-boy to create users. SSO tests mock the integration layer.

```python
# tests/test_services.py (excerpt)
from django.test import TestCase
from identity.services.auth_service import AuthService
from tests.factories import UserFactory


class AuthServiceTest(TestCase):
    def setUp(self):
        self.user = UserFactory(password="TestPass123!")

    def test_login_success(self):
        result = AuthService.login(
            email=self.user.email, password="TestPass123!"
        )
        self.assertIn("access_token", result)
        self.assertIn("refresh_token", result)
```

### Test Example: Infrastructure Tests (`tests/test_infrastructure.py`)
```python
# tests/test_infrastructure.py (excerpt)
from unittest.mock import MagicMock, patch
from django.test import TestCase
from identity.infrastructure.event_publisher import EventPublisher


class EventPublisherTest(TestCase):
    @patch("identity.infrastructure.event_publisher.redis.Redis")
    def test_publish_success(self, mock_redis_cls):
        mock_client = MagicMock()
        mock_redis_cls.return_value = mock_client

        EventPublisher.publish("user_registered", {"user_id": "123"})

        mock_client.xadd.assert_called_once()
```

### Test Example: API Integration Tests (`tests/test_api.py`)
API tests use `ninja.testing.TestClient` to exercise the full request/response cycle.

```python
# tests/test_api.py (excerpt)
from django.test import TestCase
from ninja.testing import TestClient
from identity.api.routers import api
from tests.factories import UserFactory


class AuthAPITest(TestCase):
    def setUp(self):
        super().setUp()
        self.client = TestClient(api)
        self.user = UserFactory(password="TestPass123!")

    def test_login_success(self):
        response = self.client.post(
            "/auth/login",
            json={"email": self.user.email, "password": "TestPass123!"},
        )
        self.assertEqual(response.status_code, 200)
```

---

## Logging and Observability

### Architecture
The Auth microservice adheres to the 12-Factor App methodology for logging. All logs are written directly to standard output (`stdout`) as structured JSON objects.

### Correlation IDs (Request Tracing)
Every incoming HTTP request is assigned a unique `X-Request-ID`. To ensure that the `request_id` is attached to all logs across all layers, we **explicitly pass it as a function argument** from the API Controller down to the Services. We intentionally avoid `contextvars` to keep function signatures transparent and testable.

### Implementation

#### Settings Configuration (`config/settings.py`)
```python
# config/settings.py (logging excerpt)
LOG_LEVEL = env("LOG_LEVEL")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(asctime)s %(levelname)s %(name)s %(message)s %(request_id)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
            "stream": "ext://sys.stdout",
        },
    },
    "loggers": {
        "django": {"handlers": ["console"], "level": LOG_LEVEL, "propagate": False},
        "identity": {"handlers": ["console"], "level": LOG_LEVEL, "propagate": False},
    },
    "root": {"handlers": ["console"], "level": LOG_LEVEL},
}
```

#### Request ID Middleware (`identity/api/middleware.py`)
```python
# identity/api/middleware.py
import logging
import uuid
from collections.abc import Callable

from django.http import HttpRequest, HttpResponse

logger = logging.getLogger("identity.middleware")


class RequestIDMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        setattr(request, "request_id", request_id)
        logger.info(
            "Incoming request: %s %s",
            request.method,
            request.path,
            extra={"request_id": request_id},
        )

        response = self.get_response(request)
        response["X-Request-ID"] = request_id
        return response
```

#### Usage in Services (`identity/services/auth_service.py`)
```python
# identity/services/auth_service.py (excerpt)
import logging

logger = logging.getLogger("identity.services.auth_service")


class AuthService:
    @staticmethod
    def login(email, password, request_id=None):
        extra = {"request_id": request_id} if request_id else {}

        user = authenticate(username=email, password=password)
        if user is None:
            logger.warning("Failed login attempt for email: %s", email, extra=extra)
            raise InvalidCredentialsError("Invalid email or password.")

        logger.info(
            "User logged in successfully: %s",
            user.id,
            extra={**extra, "user_id": str(user.id)},
        )
```

## Related documents
- [REST API (Django Ninja)](api/rest-api.md)
- [Identity & Users](domains/identity-and-users.md)
- [Token Management & Security](domains/token-management.md)
- [Authentication & Sessions](domains/authentication-and-sessions.md)
- [Account Lifecycle & Events](domains/account-lifecycle.md)
- [Multi-Factor Authentication (MFA)](domains/mfa.md)
- [Single Sign-On (SSO)](domains/sso.md)