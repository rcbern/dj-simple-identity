# Domain: Token Management & Security

> **Section 6** of the Auth Microservice Architecture Specification. See [`README.md`](../README.md) for the full index.

### The Hybrid JWT Strategy & Simple Rotation
1. **Generation:** A 48-character cryptographically secure opaque string is generated.
2. **Storage:** The string is hashed via SHA-256 and stored in the `Token.token_hash` DB column.
3. **Delivery:** The *raw* opaque string is placed inside a JWT payload. This JWT is returned to the client.
4. **Validation:** The Auth service decodes the JWT, hashes the opaque string, and queries the DB.
5. **Rotation:** On `/refresh`, the old token is deleted and a new one is issued. The implementation intentionally omits session-family tracking and reuse detection — brute-force protection is delegated to the gateway's rate limiter.

### Model Definition: `Token` (`identity/models/token.py`)
The `Token` model is intentionally lean — it stores only the hash, type, expiry, and user. There are no `session_family`, `is_revoked`, or `attempts` fields.

```python
# identity/models/token.py
import hashlib
import secrets
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class TokenType(models.TextChoices):
    REFRESH = "REFRESH", "Refresh Token"
    EMAIL_VERIFY = "EMAIL_VERIFY", "Email Verification"
    PASSWORD_RESET = "PASSWORD_RESET", "Password Reset"
    MFA_CHALLENGE = "MFA_CHALLENGE", "MFA Challenge"


class Token(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="tokens"
    )
    token_type = models.CharField(
        max_length=20, choices=TokenType.choices, db_index=True
    )
    token_hash = models.CharField(max_length=64, unique=True, db_index=True)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    @classmethod
    def generate_opaque_string(cls):
        return secrets.token_urlsafe(48)

    @classmethod
    def hash_token(cls, raw_token):
        return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

    @property
    def is_valid(self):
        return timezone.now() < self.expires_at
```

### Service Definition: `TokenService` (`identity/services/token_service.py`)
```python
# identity/services/token_service.py
import logging
from datetime import UTC, datetime, timedelta

import jwt
from django.conf import settings
from django.db import transaction

from identity.models.token import Token, TokenType
from identity.models.user import User

logger = logging.getLogger("identity.services.token_service")


class TokenService:
    @staticmethod
    def issue_token(user: User, token_type: str, expiry_delta: timedelta) -> str:
        raw_opaque = Token.generate_opaque_string()
        token_hash = Token.hash_token(raw_opaque)
        expires_at = datetime.now(UTC) + expiry_delta

        with transaction.atomic():
            # Enforce 1 token per type per user (except multi-device refresh)
            if token_type == TokenType.REFRESH:
                if not getattr(settings, "ALLOW_MULTI_DEVICE_REFRESH_TOKENS", False):
                    Token.objects.filter(user=user, token_type=token_type).delete()
            else:
                Token.objects.filter(user=user, token_type=token_type).delete()

            Token.objects.create(
                user=user,
                token_type=token_type,
                token_hash=token_hash,
                expires_at=expires_at,
            )

        payload = {
            "user_id": str(user.id),
            "token": raw_opaque,
            "type": token_type,
            "exp": expires_at,
            "iat": datetime.now(UTC),
        }
        return jwt.encode(payload, settings.JWT_PRIVATE_KEY, algorithm="RS256")

    @staticmethod
    def decode_and_validate_token(raw_jwt: str, token_type: str) -> Token | None:
        try:
            payload = jwt.decode(raw_jwt, settings.JWT_PUBLIC_KEY, algorithms=["RS256"])
        except jwt.PyJWTError:
            return None

        raw_opaque = payload.get("token")
        if not raw_opaque:
            return None

        token_hash = Token.hash_token(raw_opaque)
        try:
            token = Token.objects.get(token_hash=token_hash, token_type=token_type)
        except Token.DoesNotExist:
            return None  # Token was deleted (logged out or rotated)

        if not token.is_valid:
            token.delete()
            return None
        return token
```

## Related documents
- [Overview](../overview.md)
- [Architectural Decisions Summary](../architectural-decisions.md)
- [Directory Structure](../directory-structure.md)
- [Identity & Users](identity-and-users.md)
- [Authentication & Sessions](authentication-and-sessions.md)
- [Account Lifecycle & Events](account-lifecycle.md)
- [Multi-Factor Authentication (MFA)](mfa.md)
- [Single Sign-On (SSO)](sso.md)
- [REST API (Django Ninja)](../api/rest-api.md)