# Domain: Multi-Factor Authentication (MFA)

> **Section 9** of the Auth Microservice Architecture Specification. See [`README.md`](../README.md) for the full index.

### Model Definition: `UserMFA` (`auth/models/mfa.py`)
Strictly handles TOTP. Secrets are encrypted at rest using Fernet.

```python
import uuid
from django.db import models
from django.conf import settings

class MFAType(models.TextChoices):
    TOTP = 'TOTP', 'Authenticator App'

class UserMFA(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='mfa')
    secret = models.CharField(max_length=255) # Encrypted Fernet string
    mfa_type = models.CharField(max_length=10, choices=MFAType.choices, default=MFAType.TOTP)
    is_enabled = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
```

### Service Definition: `UserMFAService` (`auth/services/mfa_service.py`)
```python
import pyotp
from django.conf import settings
from cryptography.fernet import Fernet
from datetime import timedelta
from ..models.token import Token, TokenType
from ..models.mfa import UserMFA
from .token_service import TokenService

class UserMFAService:
    @staticmethod
    def _get_fernet(): return Fernet(settings.MFA_ENCRYPTION_KEY)

    @staticmethod
    def _encrypt_secret(secret: str) -> str:
        return UserMFAService._get_fernet().encrypt(secret.encode('utf-8')).decode('utf-8')

    @staticmethod
    def _decrypt_secret(encrypted_secret: str) -> str:
        return UserMFAService._get_fernet().decrypt(encrypted_secret.encode('utf-8')).decode('utf-8')

    @staticmethod
    def enroll(user):
        raw_secret = pyotp.random_base32()
        encrypted_secret = UserMFAService._encrypt_secret(raw_secret)
        UserMFA.objects.update_or_create(user=user, defaults={'secret': encrypted_secret, 'is_enabled': False})
        otpauth_uri = pyotp.totp.TOTP(raw_secret).provisioning_uri(name=user.email, issuer_name="YourAppName")
        return {'secret': raw_secret, 'otpauth_uri': otpauth_uri}

    @staticmethod
    def verify_and_enable(user, otp_code):
        try: mfa = UserMFA.objects.get(user=user)
        except UserMFA.DoesNotExist: raise ValueError("MFA enrollment not found.")

        raw_secret = UserMFAService._decrypt_secret(mfa.secret)
        totp = pyotp.TOTP(raw_secret)
        if not totp.verify(otp_code, valid_window=1): raise PermissionError("Invalid OTP code.")

        mfa.is_enabled = True
        mfa.save(update_fields=['is_enabled'])
        return True

    @staticmethod
    def issue_challenge(user):
        try: UserMFA.objects.get(user=user, is_enabled=True)
        except UserMFA.DoesNotExist: return None
            
        return TokenService.issue_token(user, TokenType.MFA_CHALLENGE, timedelta(minutes=5))

    @staticmethod
    def verify_challenge(user, otp_code, challenge_token):
        try: mfa = UserMFA.objects.get(user=user, is_enabled=True)
        except UserMFA.DoesNotExist: raise PermissionError("MFA is not enabled.")

        raw_secret = UserMFAService._decrypt_secret(mfa.secret)
        totp = pyotp.TOTP(raw_secret)
        if not totp.verify(otp_code, valid_window=1): raise PermissionError("Invalid OTP code.")

        token = TokenService.decode_and_validate_token(challenge_token, TokenType.MFA_CHALLENGE)
        if not token: raise PermissionError("Invalid or expired MFA session.")
        token.delete()
        return True
```

## Related documents
- [Overview](../overview.md)
- [Architectural Decisions Summary](../architectural-decisions.md)
- [Directory Structure](../directory-structure.md)
- [Identity & Users](identity-and-users.md)
- [Token Management & Security](token-management.md)
- [Authentication & Sessions](authentication-and-sessions.md)
- [REST API (Django Ninja)](../api/rest-api.md)