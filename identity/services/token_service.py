"""Token service for issuing and validating opaque JWT-wrapped tokens.

Implements the hybrid JWT strategy: a cryptographically secure opaque
string is generated, hashed via SHA-256, stored in the database, and
delivered to the client inside a JWT payload signed with RS256.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

import jwt
from django.conf import settings
from django.db import transaction

from identity.models.token import Token, TokenType
from identity.models.user import User

logger = logging.getLogger("identity.services.token_service")


class TokenService:
    """Issues and validates opaque tokens wrapped in RS256 JWTs."""

    @staticmethod
    def issue_token(
        user: User,
        token_type: str,
        expiry_delta: timedelta,
    ) -> str:
        """Issue a new token for a user, deleting any existing same-type token.

        Args:
            user: The user to issue the token for.
            token_type: The ``TokenType`` value for this token.
            expiry_delta: How long until the token expires.

        Returns:
            A signed JWT string containing the raw opaque token.
        """
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
    def decode_and_validate_token(
        raw_jwt: str,
        token_type: str,
    ) -> Token | None:
        """Decode a JWT, look up the opaque token in the DB, and validate it.

        Args:
            raw_jwt: The JWT string received from the client.
            token_type: The expected ``TokenType`` value.

        Returns:
            The matching ``Token`` instance if valid, otherwise ``None``.
        """
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
