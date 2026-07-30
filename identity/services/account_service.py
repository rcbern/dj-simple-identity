"""Account service for registration, email verification, and password reset.

Handles account lifecycle events. Fires events to Redis Streams instead
of sending emails directly.
"""

from __future__ import annotations

import logging
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import transaction

from identity.exceptions import TokenInvalidError, UserAlreadyExistsError
from identity.infrastructure.event_publisher import EventPublisher
from identity.models.token import Token, TokenType
from identity.models.user import User
from identity.services.token_service import TokenService

logger = logging.getLogger("identity.services.account_service")

UserModel = get_user_model()


class AccountService:
    """Handles user registration, email verification, and password resets."""

    @staticmethod
    @transaction.atomic
    def register(
        email: str,
        password: str,
        request_id: str | None = None,
    ) -> User:
        """Register a new user and fire a ``user_registered`` event.

        Args:
            email: The new user's email address.
            password: The new user's plaintext password.
            request_id: Optional correlation ID for logging.

        Returns:
            The newly created ``User`` instance.

        Raises:
            UserAlreadyExistsError: If a user with this email already exists.
        """
        if UserModel.objects.filter(email=email).exists():
            raise UserAlreadyExistsError("A user with this email already exists.")

        user = UserModel.objects.create_user(
            email=email, password=password, is_verified=False
        )
        verify_token = TokenService.issue_token(
            user, TokenType.EMAIL_VERIFY, timedelta(hours=24)
        )

        EventPublisher.publish(
            "user_registered",
            {
                "user_id": str(user.id),
                "email": user.email,
                "verify_token": verify_token,
            },
        )
        logger.info(
            "User registered: %s",
            user.id,
            extra={"request_id": request_id} if request_id else {},
        )
        return user

    @staticmethod
    def verify_email(
        verify_token: str,
        request_id: str | None = None,
    ) -> User:
        """Verify a user's email using a verification token.

        Idempotent — returns success if the user is already verified.

        Args:
            verify_token: The JWT email verification token.
            request_id: Optional correlation ID for logging.

        Returns:
            The verified ``User`` instance.

        Raises:
            TokenInvalidError: If the verification token is invalid or expired.
        """
        token = TokenService.decode_and_validate_token(
            verify_token, TokenType.EMAIL_VERIFY
        )
        if not token:
            raise TokenInvalidError("Invalid or expired verification token.")

        user = token.user
        if user.is_verified:
            token.delete()
            return user  # Idempotent: return success

        user.is_verified = True
        user.save(update_fields=["is_verified"])
        token.delete()
        logger.info(
            "Email verified for user: %s",
            user.id,
            extra={"request_id": request_id} if request_id else {},
        )
        return user

    @staticmethod
    def request_password_reset(
        email: str,
        request_id: str | None = None,
    ) -> str | None:
        """Issue a password reset token and fire a ``password_reset_requested`` event.

        Silently returns ``None`` if no user exists with the given email
        (to prevent email enumeration).

        Args:
            email: The email address to reset the password for.
            request_id: Optional correlation ID for logging.

        Returns:
            The reset token JWT string, or ``None`` if the user doesn't exist.
        """
        try:
            user = UserModel.objects.get(email=email)
        except UserModel.DoesNotExist:
            return None

        reset_token = TokenService.issue_token(
            user, TokenType.PASSWORD_RESET, timedelta(minutes=15)
        )
        EventPublisher.publish(
            "password_reset_requested",
            {
                "user_id": str(user.id),
                "email": user.email,
                "reset_token": reset_token,
            },
        )
        logger.info(
            "Password reset requested for user: %s",
            user.id,
            extra={"request_id": request_id} if request_id else {},
        )
        return reset_token

    @staticmethod
    def confirm_password_reset(
        reset_token: str,
        new_password: str,
        request_id: str | None = None,
    ) -> User:
        """Reset a user's password using a reset token.

        Also revokes all existing refresh tokens for the user.

        Args:
            reset_token: The JWT password reset token.
            new_password: The new plaintext password.
            request_id: Optional correlation ID for logging.

        Returns:
            The updated ``User`` instance.

        Raises:
            TokenInvalidError: If the reset token is invalid or expired.
        """
        token = TokenService.decode_and_validate_token(
            reset_token, TokenType.PASSWORD_RESET
        )
        if not token:
            raise TokenInvalidError("Invalid or expired reset token.")

        user = token.user
        user.change_password(new_password)
        token.delete()
        # Revoke all existing refresh tokens (force re-login)
        Token.objects.filter(user=user, token_type=TokenType.REFRESH).delete()
        logger.info(
            "Password reset completed for user: %s",
            user.id,
            extra={"request_id": request_id} if request_id else {},
        )
        return user
