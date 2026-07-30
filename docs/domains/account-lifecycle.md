# Domain: Account Lifecycle & Event-Driven Architecture

> **Section 8** of the Auth Microservice Architecture Specification. See [`README.md`](../README.md) for the full index.

### Infrastructure: `EventPublisher` (`identity/infrastructure/event_publisher.py`)
Pushes JSON messages to a Redis Stream. Uses proper logging instead of `print()`. Catches both `RedisError` and serialization errors (`TypeError`, `ValueError`) to ensure fire-and-forget semantics.

```python
# identity/infrastructure/event_publisher.py
import json
import logging
from typing import Any

import redis
from django.conf import settings

logger = logging.getLogger("identity.infrastructure.event_publisher")

STREAM_NAME = "auth_events"
STREAM_MAXLEN = 10000


class EventPublisher:
    @staticmethod
    def _get_client() -> redis.Redis:
        return redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=settings.REDIS_PASSWORD,
            decode_responses=True,
        )

    @staticmethod
    def publish(event_type: str, payload: dict[str, Any]) -> None:
        try:
            client = EventPublisher._get_client()
            client.xadd(
                name=STREAM_NAME,
                fields={
                    "event_type": event_type,
                    "payload": json.dumps(payload),
                },
                maxlen=STREAM_MAXLEN,
                approximate=True,
            )
        except redis.RedisError as exc:
            logger.error("Failed to publish event %s: %s", event_type, exc)
        except (TypeError, ValueError) as exc:
            logger.error("Failed to serialize event %s: %s", event_type, exc)
```

### Service Definition: `AccountService` (`identity/services/account_service.py`)
Handles registration and resets. Fires events instead of sending emails. Uses custom exceptions (`UserAlreadyExistsError`, `TokenInvalidError`) instead of bare `ValueError`/`PermissionError`.

```python
# identity/services/account_service.py
import logging
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import transaction

from identity.exceptions import TokenInvalidError, UserAlreadyExistsError
from identity.infrastructure.event_publisher import EventPublisher
from identity.models.token import Token, TokenType
from identity.models.user import User
from identity.services.token_service import TokenService

logger = logging.getLogger("identity.services.account_service")
UserModel = get_user_model()


class AccountService:
    @staticmethod
    @transaction.atomic
    def register(email: str, password: str, request_id: str | None = None) -> User:
        if UserModel.objects.filter(email=email).exists():
            raise UserAlreadyExistsError("A user with this email already exists.")

        user = UserModel.objects.create_user(
            email=email, password=password, is_verified=False
        )
        verify_token = TokenService.issue_token(
            user, TokenType.EMAIL_VERIFY, timedelta(hours=24)
        )

        EventPublisher.publish(
            "user_registered",
            {
                "user_id": str(user.id),
                "email": user.email,
                "verify_token": verify_token,
            },
        )
        return user

    @staticmethod
    def verify_email(verify_token: str, request_id: str | None = None) -> User:
        token = TokenService.decode_and_validate_token(
            verify_token, TokenType.EMAIL_VERIFY
        )
        if not token:
            raise TokenInvalidError("Invalid or expired verification token.")
        user = token.user
        if user.is_verified:
            token.delete()
            return user  # Idempotent: return success

        user.is_verified = True
        user.save(update_fields=["is_verified"])
        token.delete()
        return user

    @staticmethod
    def request_password_reset(email: str, request_id: str | None = None) -> str | None:
        try:
            user = UserModel.objects.get(email=email)
        except UserModel.DoesNotExist:
            return None

        reset_token = TokenService.issue_token(
            user, TokenType.PASSWORD_RESET, timedelta(minutes=15)
        )
        EventPublisher.publish(
            "password_reset_requested",
            {"user_id": str(user.id), "email": user.email, "reset_token": reset_token},
        )
        return reset_token

    @staticmethod
    def confirm_password_reset(reset_token: str, new_password: str, request_id: str | None = None) -> User:
        token = TokenService.decode_and_validate_token(
            reset_token, TokenType.PASSWORD_RESET
        )
        if not token:
            raise TokenInvalidError("Invalid or expired reset token.")

        user = token.user
        user.change_password(new_password)
        token.delete()
        Token.objects.filter(user=user, token_type=TokenType.REFRESH).delete()
        return user
```

## Related documents
- [Overview](../overview.md)
- [Architectural Decisions Summary](../architectural-decisions.md)
- [Directory Structure](../directory-structure.md)
- [Identity & Users](identity-and-users.md)
- [Token Management & Security](token-management.md)
- [Logging and Observability](../observability.md)
- [Testing Strategy](../testing.md)