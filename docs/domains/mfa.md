# Domain: Multi-Factor Authentication (MFA)

> **Section 6** of the Auth Microservice Architecture Specification. See [`README.md`](../README.md) for the full index.

### Model Definition: `UserMFA` (`identity/models/mfa.py`)
Strictly handles TOTP. Secrets are encrypted at rest using Fernet.

```python
# identity/models/mfa.py
import uuid

from django.conf import settings
from django.db import models


class MFAType(models.TextChoices):
    TOTP = "TOTP", "Authenticator App"


class UserMFA(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="mfa"
    )
    secret = models.CharField(max_length=255)  # Encrypted Fernet string
    mfa_type = models.CharField(
        max_length=10, choices=MFAType.choices, default=MFAType.TOTP
    )
    is_enabled = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
```

### Service Definition: `UserMFAService` (`identity/services/mfa_service.py`)
Uses custom exceptions (`MFAEnrollmentNotFoundError`, `InvalidOTPError`, `MFANotEnabledError`, `MFAChallengeInvalidError`) instead of bare `ValueError`/`PermissionError`.

```python
# identity/services/mfa_service.py
from datetime import timedelta

import pyotp
from cryptography.fernet import Fernet
from django.conf import settings

from identity.exceptions import (
    InvalidOTPError,
    MFAChallengeInvalidError,
    MFAEnrollmentNotFoundError,
    MFANotEnabledError,
)
from identity.models.mfa import UserMFA
from identity.models.token import TokenType
from identity.models.user import User
from identity.services.token_service import TokenService


class UserMFAService:
    @staticmethod
    def _get_fernet() -> Fernet:
        return Fernet(settings.MFA_ENCRYPTION_KEY)

    @staticmethod
    def _encrypt_secret(secret: str) -> str:
        return (
            UserMFAService._get_fernet().encrypt(secret.encode("utf-8")).decode("utf-8")
        )

    @staticmethod
    def _decrypt_secret(encrypted_secret: str) -> str:
        return (
            UserMFAService._get_fernet()
            .decrypt(encrypted_secret.encode("utf-8"))
            .decode("utf-8")
        )

    @staticmethod
    def enroll(user: User) -> dict[str, str]:
        raw_secret = pyotp.random_base32()
        encrypted_secret = UserMFAService._encrypt_secret(raw_secret)
        UserMFA.objects.update_or_create(
            user=user,
            defaults={"secret": encrypted_secret, "is_enabled": False},
        )
        otpauth_uri = pyotp.totp.TOTP(raw_secret).provisioning_uri(
            name=user.email, issuer_name="AuthService"
        )
        return {"secret": raw_secret, "otpauth_uri": otpauth_uri}

    @staticmethod
    def verify_and_enable(user: User, otp_code: str) -> bool:
        try:
            mfa = UserMFA.objects.get(user=user)
        except UserMFA.DoesNotExist:
            raise MFAEnrollmentNotFoundError("MFA enrollment not found.") from None

        raw_secret = UserMFAService._decrypt_secret(mfa.secret)
        totp = pyotp.TOTP(raw_secret)
        if not totp.verify(otp_code, valid_window=1):
            raise InvalidOTPError("Invalid OTP code.")

        mfa.is_enabled = True
        mfa.save(update_fields=["is_enabled"])
        return True

    @staticmethod
    def issue_challenge(user: User) -> str | None:
        try:
            UserMFA.objects.get(user=user, is_enabled=True)
        except UserMFA.DoesNotExist:
            return None

        return TokenService.issue_token(
            user, TokenType.MFA_CHALLENGE, timedelta(minutes=5)
        )

    @staticmethod
    def verify_challenge(user: User, otp_code: str, challenge_token: str) -> bool:
        try:
            mfa = UserMFA.objects.get(user=user, is_enabled=True)
        except UserMFA.DoesNotExist:
            raise MFANotEnabledError("MFA is not enabled.") from None

        raw_secret = UserMFAService._decrypt_secret(mfa.secret)
        totp = pyotp.TOTP(raw_secret)
        if not totp.verify(otp_code, valid_window=1):
            raise InvalidOTPError("Invalid OTP code.")

        token = TokenService.decode_and_validate_token(
            challenge_token, TokenType.MFA_CHALLENGE
        )
        if not token:
            raise MFAChallengeInvalidError("Invalid or expired MFA session.")
        token.delete()
        return True
```

## Related documents
- [Overview](../overview.md)
- [Identity & Users](identity-and-users.md)
- [Token Management & Security](token-management.md)
- [Authentication & Sessions](authentication-and-sessions.md)
- [REST API (Django Ninja)](../api/rest-api.md)
