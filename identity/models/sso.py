"""SocialAccount model for Single Sign-On (SSO).

Links a user to an external identity provider (e.g. GitHub). The
``(provider, provider_user_id)`` pair is unique, preventing duplicate
social accounts for the same external identity.
"""

from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models


class Provider(models.TextChoices):
    """Enumerates supported SSO identity providers."""

    GITHUB = "GITHUB", "GitHub"


class SocialAccount(models.Model):
    """A link between a user and an external identity provider.

    Attributes:
        id: UUID primary key.
        user: The owning local user (cascades on delete).
        provider: The SSO provider name (e.g. ``GITHUB``).
        provider_user_id: The user's unique ID at the provider.
        provider_email: The email reported by the provider.
        created_at: Auto-set on creation.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="social_accounts",
    )
    provider = models.CharField(max_length=20, choices=Provider.choices)
    provider_user_id = models.CharField(max_length=255)
    provider_email = models.EmailField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("provider", "provider_user_id")
