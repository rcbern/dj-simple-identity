"""Auth service for login, logout, refresh, and access token generation.

Handles active sessions and stateless RS256 access token generation.
Implements simple refresh token rotation (delete old, issue new).
"""

from __future__ import annotations

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
    """Handles authentication, session management, and token generation."""

    @staticmethod
    def generate_access_token(user: User) -> str:
        """Generate a stateless RS256 access token for a user.

        The token includes ``password_changed_at`` so the gateway can
        invalidate it if the user changes their password.

        Args:
            user: The user to generate the token for.

        Returns:
            A signed RS256 JWT access token string.
        """
        payload = {
            "user_id": str(user.id),
            "email": user.email,
            "pwd_changed_at": user.password_changed_at.isoformat(),
            "exp": datetime.now(UTC) + timedelta(minutes=ACCESS_TOKEN_EXPIRY_MINUTES),
            "iat": datetime.now(UTC),
        }
        return jwt.encode(payload, settings.JWT_PRIVATE_KEY, algorithm="RS256")

    @staticmethod
    def login(
        email: str,
        password: str,
        request_id: str | None = None,
    ) -> dict[str, object]:
        """Authenticate a user and issue tokens (or an MFA challenge).

        Args:
            email: The user's email address.
            password: The user's plaintext password.
            request_id: Optional correlation ID for logging.

        Returns:
            A dict with either ``access_token``/``refresh_token`` (normal
            login) or ``mfa_required``/``mfa_token`` (MFA challenge).

        Raises:
            InvalidCredentialsError: If credentials don't match.
            EmailNotVerifiedError: If the user's email is not verified.
        """
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
        logger.info(
            "User logged in successfully: %s",
            user.id,
            extra={**extra, "user_id": str(user.id)},
        )
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user_id": str(user.id),
        }

    @staticmethod
    def logout(
        user: User,
        refresh_token: str | None = None,
        request_id: str | None = None,
    ) -> None:
        """Log out a user by deleting their refresh token(s).

        Idempotent — does not raise if the token is already gone.

        Args:
            user: The user to log out.
            refresh_token: Optional specific refresh token JWT to revoke.
            request_id: Optional correlation ID for logging.
        """
        if refresh_token:
            token = TokenService.decode_and_validate_token(
                refresh_token, TokenType.REFRESH
            )
            if token:
                token.delete()
        else:
            Token.objects.filter(user=user, token_type=TokenType.REFRESH).delete()

    @staticmethod
    def refresh(
        raw_refresh_token: str,
        request_id: str | None = None,
    ) -> dict[str, str]:
        """Rotate a refresh token: delete the old one, issue a new pair.

        Args:
            raw_refresh_token: The JWT refresh token from the client.
            request_id: Optional correlation ID for logging.

        Returns:
            A dict with new ``access_token`` and ``refresh_token``.

        Raises:
            TokenInvalidError: If the refresh token is invalid or expired.
        """
        token = TokenService.decode_and_validate_token(
            raw_refresh_token, TokenType.REFRESH
        )
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
