"""MFA service for TOTP enrollment, verification, and challenge issuance.

Secrets are encrypted at rest using Fernet symmetric encryption. The
service handles enrollment (generate secret), verification (enable MFA),
and challenge issuance/verification during login.
"""

from __future__ import annotations

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
    """Handles TOTP-based multi-factor authentication."""

    @staticmethod
    def _get_fernet() -> Fernet:
        """Create a Fernet instance from the configured encryption key.

        Returns:
            A ``Fernet`` instance for encrypting/decrypting TOTP secrets.
        """
        return Fernet(settings.MFA_ENCRYPTION_KEY)

    @staticmethod
    def _encrypt_secret(secret: str) -> str:
        """Encrypt a raw TOTP secret using Fernet.

        Args:
            secret: The raw base32 TOTP secret.

        Returns:
            The Fernet-encrypted secret as a UTF-8 string.
        """
        return (
            UserMFAService._get_fernet().encrypt(secret.encode("utf-8")).decode("utf-8")
        )

    @staticmethod
    def _decrypt_secret(encrypted_secret: str) -> str:
        """Decrypt a Fernet-encrypted TOTP secret.

        Args:
            encrypted_secret: The Fernet-encrypted secret string.

        Returns:
            The raw base32 TOTP secret.
        """
        return (
            UserMFAService._get_fernet()
            .decrypt(encrypted_secret.encode("utf-8"))
            .decode("utf-8")
        )

    @staticmethod
    def enroll(user: User) -> dict[str, str]:
        """Enroll a user in MFA by generating a new TOTP secret.

        Creates or updates the ``UserMFA`` record with an encrypted secret.
        MFA is not enabled until the user verifies with an OTP code.

        Args:
            user: The user to enroll.

        Returns:
            A dict with ``secret`` (raw base32) and ``otpauth_uri`` for
            QR code generation.
        """
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
        """Verify an OTP code and enable MFA for the user.

        Args:
            user: The user with a pending MFA enrollment.
            otp_code: The 6-digit TOTP code from the authenticator app.

        Returns:
            ``True`` if MFA was successfully enabled.

        Raises:
            MFAEnrollmentNotFoundError: If no MFA enrollment exists.
            InvalidOTPError: If the OTP code is incorrect.
        """
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
        """Issue an MFA challenge token if the user has MFA enabled.

        Args:
            user: The user attempting to log in.

        Returns:
            A signed JWT challenge token, or ``None`` if MFA is not enabled.
        """
        try:
            UserMFA.objects.get(user=user, is_enabled=True)
        except UserMFA.DoesNotExist:
            return None

        return TokenService.issue_token(
            user, TokenType.MFA_CHALLENGE, timedelta(minutes=5)
        )

    @staticmethod
    def verify_challenge(user: User, otp_code: str, challenge_token: str) -> bool:
        """Verify an MFA challenge: both the OTP code and the challenge token.

        Args:
            user: The user verifying MFA.
            otp_code: The 6-digit TOTP code.
            challenge_token: The JWT challenge token issued during login.

        Returns:
            ``True`` if both the OTP and challenge token are valid.

        Raises:
            MFANotEnabledError: If MFA is not enabled for the user.
            InvalidOTPError: If the OTP code is incorrect.
            MFAChallengeInvalidError: If the challenge token is invalid.
        """
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
