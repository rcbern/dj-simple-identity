# Domain: Authentication & Sessions

> **Section 4** of the Auth Microservice Architecture Specification. See [`README.md`](../README.md) for the full index.

### Architecture
The `AuthService` handles active sessions and stateless Access Token generation (RS256). It implements simple refresh token rotation (delete old, issue new — no session families or reuse detection).

### Service Definition: `AuthService` (`identity/services/auth_service.py`)
```python
# identity/services/auth_service.py
import logging
from datetime import UTC, datetime, timedelta

import jwt
from django.conf import settings
from django.contrib.auth import authenticate

from identity.exceptions import (
    EmailNotVerifiedError,
    InvalidCredentialsError,
    TokenInvalidError,
)
from identity.models.token import Token, TokenType
from identity.models.user import User
from identity.services.mfa_service import UserMFAService
from identity.services.token_service import TokenService

logger = logging.getLogger("identity.services.auth_service")

ACCESS_TOKEN_EXPIRY_MINUTES = 15
REFRESH_TOKEN_EXPIRY_DAYS = 7


class AuthService:
    @staticmethod
    def generate_access_token(user: User) -> str:
        payload = {
            "user_id": str(user.id),
            "email": user.email,
            "pwd_changed_at": user.password_changed_at.isoformat(),
            "exp": datetime.now(UTC) + timedelta(minutes=ACCESS_TOKEN_EXPIRY_MINUTES),
            "iat": datetime.now(UTC),
        }
        return jwt.encode(payload, settings.JWT_PRIVATE_KEY, algorithm="RS256")

    @staticmethod
    def login(email: str, password: str, request_id: str | None = None) -> dict[str, object]:
        extra: dict[str, str] = {"request_id": request_id} if request_id else {}

        user = authenticate(username=email, password=password)
        if user is None:
            logger.warning("Failed login attempt for email: %s", email, extra=extra)
            raise InvalidCredentialsError("Invalid email or password.")

        if not user.is_verified:
            raise EmailNotVerifiedError("Email not verified.")

        mfa_challenge = UserMFAService.issue_challenge(user)
        if mfa_challenge:
            return {
                "mfa_required": True,
                "mfa_token": mfa_challenge,
                "user_id": str(user.id),
            }

        access_token = AuthService.generate_access_token(user)
        refresh_token = TokenService.issue_token(
            user, TokenType.REFRESH, timedelta(days=REFRESH_TOKEN_EXPIRY_DAYS)
        )
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user_id": str(user.id),
        }

    @staticmethod
    def logout(user: User, refresh_token: str | None = None, request_id: str | None = None) -> None:
        # Idempotent: doesn't throw if token is already gone
        if refresh_token:
            token = TokenService.decode_and_validate_token(refresh_token, TokenType.REFRESH)
            if token:
                token.delete()
        else:
            Token.objects.filter(user=user, token_type=TokenType.REFRESH).delete()

    @staticmethod
    def refresh(raw_refresh_token: str, request_id: str | None = None) -> dict[str, str]:
        token = TokenService.decode_and_validate_token(raw_refresh_token, TokenType.REFRESH)
        if not token:
            raise TokenInvalidError("Invalid or expired refresh token.")

        user = token.user

        # Simple rotation: delete the old token, issue a new one
        token.delete()

        new_refresh_token = TokenService.issue_token(
            user=user,
            token_type=TokenType.REFRESH,
            expiry_delta=timedelta(days=REFRESH_TOKEN_EXPIRY_DAYS),
        )
        new_access_token = AuthService.generate_access_token(user)
        return {
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,
            "user_id": str(user.id),
        }
```

## Related documents
- [Overview](../overview.md)
- [Identity & Users](identity-and-users.md)
- [Token Management & Security](token-management.md)
- [Multi-Factor Authentication (MFA)](mfa.md)
- [Single Sign-On (SSO)](sso.md)
- [REST API (Django Ninja)](../api/rest-api.md)
