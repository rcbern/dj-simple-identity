# Domain: Account Lifecycle & Event-Driven Architecture

> **Section 8** of the Auth Microservice Architecture Specification. See [`README.md`](../README.md) for the full index.

### Infrastructure: `EventPublisher` (`auth/infrastructure/event_publisher.py`)
Pushes JSON messages to a Redis Stream. Uses proper logging instead of `print()`.

```python
import json
import redis
import logging
from django.conf import settings

logger = logging.getLogger('auth.infrastructure.event_publisher')

class EventPublisher:
    @staticmethod
    def _get_client():
        return redis.Redis(
            host=settings.REDIS_HOST, port=settings.REDIS_PORT,
            password=getattr(settings, 'REDIS_PASSWORD', None),
            decode_responses=True
        )

    @staticmethod
    def publish(event_type: str, payload: dict):
        try:
            client = EventPublisher._get_client()
            client.xadd(
                name='auth_events', 
                fields={'event_type': event_type, 'payload': json.dumps(payload)},
                maxlen=10000, approximate=True 
            )
        except Exception as e:
            logger.error(f"Failed to publish event {event_type}: {e}")
```

### Service Definition: `AccountService` (`auth/services/account_service.py`)
Handles registration and resets. Fires events instead of sending emails.

```python
from django.db import transaction
from django.contrib.auth import get_user_model
from datetime import timedelta
from ..models.token import Token, TokenType
from .token_service import TokenService
from ..infrastructure.event_publisher import EventPublisher

User = get_user_model()

class AccountService:
    @staticmethod
    @transaction.atomic
    def register(email, password, request_id=None):
        if User.objects.filter(email=email).exists():
            raise ValueError("A user with this email already exists.")
            
        user = User.objects.create_user(email=email, password=password, is_verified=False)
        verify_token = TokenService.issue_token(user, TokenType.EMAIL_VERIFY, timedelta(hours=24))
        
        EventPublisher.publish('user_registered', {
            'user_id': str(user.id), 'email': user.email, 'verify_token': verify_token
        })
        return user

    @staticmethod
    def verify_email(verify_token, request_id=None):
        token = TokenService.decode_and_validate_token(verify_token, TokenType.EMAIL_VERIFY)
        if not token: raise PermissionError("Invalid or expired verification token.")
        user = token.user
        if user.is_verified:
            token.delete()
            return user # Idempotent: return success
            
        user.is_verified = True
        user.save(update_fields=['is_verified'])
        token.delete()
        return user

    @staticmethod
    def request_password_reset(email, request_id=None):
        try: user = User.objects.get(email=email)
        except User.DoesNotExist: return None
            
        reset_token = TokenService.issue_token(user, TokenType.PASSWORD_RESET, timedelta(minutes=15))
        EventPublisher.publish('password_reset_requested', {
            'user_id': str(user.id), 'email': user.email, 'reset_token': reset_token
        })
        return reset_token

    @staticmethod
    def confirm_password_reset(reset_token, new_password, request_id=None):
        token = TokenService.decode_and_validate_token(reset_token, TokenType.PASSWORD_RESET)
        if not token: raise PermissionError("Invalid or expired reset token.")
            
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