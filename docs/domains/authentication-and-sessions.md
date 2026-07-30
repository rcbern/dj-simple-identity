# Domain: Authentication & Sessions

> **Section 7** of the Auth Microservice Architecture Specification. See [`README.md`](../README.md) for the full index.

### Architecture
The `AuthService` handles active sessions and stateless Access Token generation (RS256). It implements Refresh Token Rotation and sets HttpOnly cookies.

### Service Definition: `AuthService` (`auth/services/auth_service.py`)
```python
import jwt
import logging
from datetime import datetime, timedelta, timezone
from django.conf import settings
from django.contrib.auth import authenticate
from .token_service import TokenService
from .mfa_service import UserMFAService

logger = logging.getLogger('auth.services.auth_service')

class AuthService:
    @staticmethod
    def generate_access_token(user):  # Public, used by SSO service
        payload = {
            'user_id': str(user.id), 'email': user.email,
            'pwd_changed_at': user.password_changed_at.isoformat(),
            'exp': datetime.now(timezone.utc) + timedelta(minutes=15),
            'iat': datetime.now(timezone.utc),
        }
        return jwt.encode(payload, settings.JWT_PRIVATE_KEY, algorithm='RS256')

    @staticmethod
    def login(email, password, request_id=None):
        extra = {'request_id': request_id} if request_id else {}
        user = authenticate(username=email, password=password)
        if user is None:
            logger.warning(f"Failed login attempt for email: {email}", extra=extra)
            raise ValueError("Invalid email or password.")
        if not user.is_verified:
            raise PermissionError("Email not verified.")

        mfa_challenge = UserMFAService.issue_challenge(user)
        if mfa_challenge:
            return {'mfa_required': True, 'mfa_token': mfa_challenge, 'user_id': str(user.id)}

        access_token = AuthService.generate_access_token(user)
        refresh_token = TokenService.issue_token(user, TokenType.REFRESH, timedelta(days=7))
        return {'access_token': access_token, 'refresh_token': refresh_token, 'user_id': str(user.id)}

    @staticmethod
    def logout(user, refresh_token=None, request_id=None):
        # Idempotent: doesn't throw if token is already gone
        if refresh_token:
            token = TokenService.decode_and_validate_token(refresh_token, TokenType.REFRESH)
            if token: token.delete()
        else:
            Token.objects.filter(user=user, token_type=TokenType.REFRESH).delete()

    @staticmethod
    def refresh(raw_refresh_token, request_id=None):
        token = TokenService.decode_and_validate_token(raw_refresh_token, TokenType.REFRESH)
        if not token:
            raise PermissionError("Invalid or expired refresh token.")

        user = token.user

        # Rotation: Revoke old, issue new in same family
        token.is_revoked = True
        token.save(update_fields=['is_revoked'])
        
        new_refresh_token = TokenService.issue_token(
            user=user, token_type=TokenType.REFRESH,
            expiry_delta=timedelta(days=7),
            session_family=token.session_family
        )
        new_access_token = AuthService.generate_access_token(user)
        return {'access_token': new_access_token, 'refresh_token': new_refresh_token}
```

## Related documents
- [Overview](../overview.md)
- [Architectural Decisions Summary](../architectural-decisions.md)
- [Directory Structure](../directory-structure.md)
- [Identity & Users](identity-and-users.md)
- [Token Management & Security](token-management.md)
- [Multi-Factor Authentication (MFA)](mfa.md)
- [Single Sign-On (SSO)](sso.md)
- [REST API (Django Ninja)](../api/rest-api.md)
- [Logging and Observability](../observability.md)