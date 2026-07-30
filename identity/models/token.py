"""Unified Token model for the Auth microservice.

Supports refresh tokens, email verification, password reset, and MFA
challenges. Implements rotation, reuse detection (via ``session_family``),
and brute-force protection (via ``attempts``).
"""

from __future__ import annotations

import hashlib
import secrets
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class TokenType(models.TextChoices):
    """Enumerates the kinds of opaque tokens the service issues."""

    REFRESH = "REFRESH", "Refresh Token"
    EMAIL_VERIFY = "EMAIL_VERIFY", "Email Verification"
    PASSWORD_RESET = "PASSWORD_RESET", "Password Reset"
    MFA_CHALLENGE = "MFA_CHALLENGE", "MFA Challenge"


class Token(models.Model):
    """A database-backed opaque token used for various auth flows.

    The raw opaque string is delivered to the client inside a JWT payload.
    Only the SHA-256 hash of the string is stored in ``token_hash``.

    Attributes:
        id: UUID primary key (prevents integer enumeration).
        user: The owning user (cascades on delete).
        token_type: The flow this token belongs to (refresh, verify, etc.).
        token_hash: SHA-256 hash of the raw opaque string (unique, indexed).
        expires_at: When the token becomes invalid.
        created_at: Auto-set on creation.
        session_family: Groups rotated refresh tokens for reuse detection.
        is_revoked: Whether this token has been explicitly revoked.
        attempts: Failed verification attempts (brute-force protection).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="tokens",
    )
    token_type = models.CharField(
        max_length=20, choices=TokenType.choices, db_index=True
    )
    token_hash = models.CharField(max_length=64, unique=True, db_index=True)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    # Rotation & reuse detection
    session_family = models.UUIDField(default=uuid.uuid4, db_index=True)
    is_revoked = models.BooleanField(default=False)

    # Brute-force protection for MFA/Verify codes
    attempts = models.IntegerField(default=0)

    class Meta:
        ordering = ["-created_at"]

    @classmethod
    def generate_opaque_string(cls) -> str:
        """Generate a 48-character cryptographically secure opaque string.

        Returns:
            A URL-safe base64-encoded random string.
        """
        return secrets.token_urlsafe(48)

    @classmethod
    def hash_token(cls, raw_token: str) -> str:
        """Hash a raw opaque token via SHA-256 for safe DB storage.

        Args:
            raw_token: The plaintext opaque string from the JWT payload.

        Returns:
            A 64-character hex digest.
        """
        return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

    @property
    def is_valid(self) -> bool:
        """Whether this token is still usable.

        Returns:
            ``False`` if revoked, exhausted (>= 5 attempts), or expired;
            otherwise ``True``.
        """
        if self.is_revoked or self.attempts >= 5:
            return False
        return timezone.now() < self.expires_at
