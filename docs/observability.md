# Logging and Observability

> **Section 13** of the Auth Microservice Architecture Specification. See [`README.md`](README.md) for the full index.

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
- [Overview](overview.md)
- [Architectural Decisions Summary](architectural-decisions.md)
- [Directory Structure](directory-structure.md)
- [Authentication & Sessions](domains/authentication-and-sessions.md)
- [REST API (Django Ninja)](api/rest-api.md)
- [Testing Strategy](testing.md)