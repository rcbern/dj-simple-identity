"""SSO service for social login and registration.

Uses the Dependency Inversion Principle — SSO integrations are resolved
via the factory in ``identity.integrations.sso``. Includes email
collision protection: if a user logs in with a social provider but
already has an unverified local account, the merge is refused.
"""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from django.db import transaction

from identity.exceptions import SSOEmailCollisionError
from identity.integrations.sso import get_sso_service
from identity.models.sso import SocialAccount
from identity.models.token import TokenType
from identity.models.user import User
from identity.services.auth_service import AuthService
from identity.services.token_service import TokenService

logger = logging.getLogger("identity.services.sso_service")

REFRESH_TOKEN_EXPIRY_DAYS = 7


class SSOService:
    """Handles social login and registration via external providers."""

    @staticmethod
    @transaction.atomic
    def login_or_register(
        provider_name: str,
        code: str,
        request_id: str | None = None,
    ) -> dict[str, Any]:
        """Log in or register a user via an SSO provider.

        If a ``SocialAccount`` exists for the provider + provider_user_id,
        the linked user is logged in. Otherwise, a new user is created
        (or an existing local account is linked, if verified).

        Args:
            provider_name: The SSO provider name (e.g. ``"GITHUB"``).
            code: The authorization code from the OAuth callback.
            request_id: Optional correlation ID for logging.

        Returns:
            A dict with ``access_token``, ``refresh_token``, and ``user_id``.

        Raises:
            SSOEmailCollisionError: If the provider email matches an
                unverified local account.
        """
        sso_integration = get_sso_service(provider_name)
        provider_user_id, provider_email = sso_integration.exchange_code_and_get_user(
            code
        )

        try:
            social_account = SocialAccount.objects.select_related("user").get(
                provider=provider_name, provider_user_id=provider_user_id
            )
            user = social_account.user
        except SocialAccount.DoesNotExist:
            try:
                user = User.objects.get(email=provider_email)
                # Collision protection: block merge if local account is
                # unverified
                if not user.is_verified:
                    raise SSOEmailCollisionError(
                        "An account with this email exists but is not "
                        "verified. Please log in with your password to "
                        "verify and link accounts."
                    )
            except User.DoesNotExist:
                user = User.objects.create_user(
                    email=provider_email, is_verified=True, password=None
                )

            SocialAccount.objects.create(
                user=user,
                provider=provider_name,
                provider_user_id=provider_user_id,
                provider_email=provider_email,
            )

        access_token = AuthService.generate_access_token(user)
        refresh_token = TokenService.issue_token(
            user, TokenType.REFRESH, timedelta(days=REFRESH_TOKEN_EXPIRY_DAYS)
        )
        logger.info(
            "SSO login successful for user: %s via %s",
            user.id,
            provider_name,
            extra={"request_id": request_id} if request_id else {},
        )
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user_id": str(user.id),
        }
