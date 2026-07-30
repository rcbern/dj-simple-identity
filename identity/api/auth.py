"""JWT authentication backend for Django Ninja.

Validates RS256 access tokens issued by ``AuthService.generate_access_token``.
The token is stateless — no database lookup is needed. The gateway is
expected to forward the token in the ``Authorization: Bearer <token>`` header.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

import jwt
from django.conf import settings
from django.contrib.auth import get_user_model
from ninja.security import HttpBearer

logger = logging.getLogger("identity.api.auth")

UserModel = get_user_model()


class JWTAuth(HttpBearer):
    """Django Ninja bearer auth that validates RS256 access tokens.

    The access token is stateless — it contains ``user_id``, ``email``,
    ``pwd_changed_at``, ``exp``, and ``iat`` claims. No database lookup
    is performed; the authenticated user is fetched by ``user_id``.
    """

    def authenticate(self, request, token: str):  # type: ignore[override]
        """Validate the JWT and return the authenticated user.

        Args:
            request: The Django HttpRequest.
            token: The raw JWT string from the Authorization header.

        Returns:
            The ``User`` instance if valid, otherwise ``None``.
        """
        try:
            payload = jwt.decode(token, settings.JWT_PUBLIC_KEY, algorithms=["RS256"])
        except jwt.PyJWTError:
            logger.warning("Invalid JWT received")
            return None

        # Check expiry explicitly (pyjwt handles exp, but be defensive)
        exp = payload.get("exp")
        if exp and datetime.now(UTC).timestamp() > exp:
            logger.warning("Expired JWT received")
            return None

        user_id = payload.get("user_id")
        if not user_id:
            return None

        try:
            return UserModel.objects.get(id=user_id)
        except UserModel.DoesNotExist:
            logger.warning("JWT user not found: %s", user_id)
            return None
