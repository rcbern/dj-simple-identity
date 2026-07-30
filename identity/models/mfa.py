"""UserMFA model for multi-factor authentication.

Strictly handles TOTP (Time-based One-Time Password). Secrets are
encrypted at rest using Fernet symmetric encryption.
"""

from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models


class MFAType(models.TextChoices):
    """Enumerates supported MFA methods."""

    TOTP = "TOTP", "Authenticator App"


class UserMFA(models.Model):
    """A user's MFA configuration (one-to-one with ``User``).

    The ``secret`` field stores a Fernet-encrypted TOTP secret. The raw
    secret is never persisted — it is decrypted only in-memory during
    verification.

    Attributes:
        id: UUID primary key.
        user: One-to-one link to the owning user (cascades on delete).
        secret: Fernet-encrypted TOTP secret string.
        mfa_type: The MFA method (currently only TOTP).
        is_enabled: Whether MFA is active for this user.
        created_at: Auto-set on creation.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="mfa",
    )
    secret = models.CharField(max_length=255)  # Encrypted Fernet string
    mfa_type = models.CharField(
        max_length=10, choices=MFAType.choices, default=MFAType.TOTP
    )
    is_enabled = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
