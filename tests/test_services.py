"""Unit tests for the service layer.

Covers ``TokenService``, ``AuthService``, ``AccountService``,
``UserMFAService``, and ``SSOService``.
"""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import MagicMock, patch

import jwt
import pyotp
from django.conf import settings
from django.test import TestCase

from identity.exceptions import (
    EmailNotVerifiedError,
    InvalidCredentialsError,
    InvalidOTPError,
    MFAEnrollmentNotFoundError,
    SSOEmailCollisionError,
    TokenInvalidError,
    UserAlreadyExistsError,
)
from identity.models.token import Token, TokenType
from identity.models.user import User
from identity.services.account_service import AccountService
from identity.services.auth_service import AuthService
from identity.services.mfa_service import UserMFAService
from identity.services.sso_service import SSOService
from identity.services.token_service import TokenService
from tests.factories import UserFactory


class TokenServiceTest(TestCase):
    """Tests for ``TokenService``."""

    def setUp(self) -> None:
        """Create a verified user for token issuance."""
        self.user = UserFactory()

    def test_issue_token_creates_db_record(self) -> None:
        """Issuing a token should create a ``Token`` record in the DB."""
        jwt_str = TokenService.issue_token(
            self.user, TokenType.REFRESH, timedelta(days=7)
        )
        self.assertTrue(jwt_str)
        self.assertEqual(
            Token.objects.filter(user=self.user, token_type=TokenType.REFRESH).count(),
            1,
        )

    def test_issue_token_deletes_old_same_type(self) -> None:
        """Issuing a new token should delete the old one of the same type."""
        TokenService.issue_token(self.user, TokenType.REFRESH, timedelta(days=7))
        TokenService.issue_token(self.user, TokenType.REFRESH, timedelta(days=7))
        self.assertEqual(
            Token.objects.filter(user=self.user, token_type=TokenType.REFRESH).count(),
            1,
        )

    def test_decode_and_validate_valid_token(self) -> None:
        """A valid JWT should decode and return the matching ``Token``."""
        jwt_str = TokenService.issue_token(
            self.user, TokenType.EMAIL_VERIFY, timedelta(hours=24)
        )
        token = TokenService.decode_and_validate_token(jwt_str, TokenType.EMAIL_VERIFY)
        self.assertIsNotNone(token)
        assert token is not None
        self.assertEqual(token.user, self.user)

    def test_decode_and_validate_invalid_jwt(self) -> None:
        """An invalid JWT string should return ``None``."""
        result = TokenService.decode_and_validate_token(
            "invalid.jwt.string", TokenType.REFRESH
        )
        self.assertIsNone(result)

    def test_decode_and_validate_deleted_token(self) -> None:
        """A token that was deleted from the DB should return ``None``."""
        jwt_str = TokenService.issue_token(
            self.user, TokenType.REFRESH, timedelta(days=7)
        )
        Token.objects.filter(user=self.user).delete()
        result = TokenService.decode_and_validate_token(jwt_str, TokenType.REFRESH)
        self.assertIsNone(result)


class AuthServiceTest(TestCase):
    """Tests for ``AuthService``."""

    def setUp(self) -> None:
        """Create a verified user with a known password."""
        self.user = UserFactory(password="TestPass123!")

    def test_login_success(self) -> None:
        """Valid credentials should return access and refresh tokens."""
        result = AuthService.login(email=self.user.email, password="TestPass123!")
        self.assertIn("access_token", result)
        self.assertIn("refresh_token", result)

    def test_login_invalid_credentials(self) -> None:
        """Invalid credentials should raise ``InvalidCredentialsError``."""
        with self.assertRaises(InvalidCredentialsError):
            AuthService.login(email=self.user.email, password="WrongPassword!")

    def test_login_unverified_email(self) -> None:
        """An unverified user should raise ``EmailNotVerifiedError``."""
        unverified = UserFactory(is_verified=False, password="TestPass123!")
        with self.assertRaises(EmailNotVerifiedError):
            AuthService.login(email=unverified.email, password="TestPass123!")

    def test_login_with_mfa_returns_challenge(self) -> None:
        """A user with MFA enabled should get an MFA challenge instead of tokens."""
        from tests.factories import UserMFAFactory

        UserMFAFactory(user=self.user, is_enabled=True)
        result = AuthService.login(email=self.user.email, password="TestPass123!")
        self.assertTrue(result.get("mfa_required"))
        self.assertIn("mfa_token", result)

    def test_refresh_rotates_token(self) -> None:
        """Refreshing should delete the old token and issue a new pair."""
        jwt_str = TokenService.issue_token(
            self.user, TokenType.REFRESH, timedelta(days=7)
        )
        result = AuthService.refresh(raw_refresh_token=jwt_str)
        self.assertIn("access_token", result)
        self.assertIn("refresh_token", result)
        # Old token should be deleted
        self.assertEqual(
            Token.objects.filter(user=self.user, token_type=TokenType.REFRESH).count(),
            1,
        )

    def test_refresh_invalid_token(self) -> None:
        """An invalid refresh token should raise ``TokenInvalidError``."""
        with self.assertRaises(TokenInvalidError):
            AuthService.refresh(raw_refresh_token="invalid.jwt.string")

    def test_logout_deletes_refresh_token(self) -> None:
        """Logout should delete the user's refresh token from the DB."""
        jwt_str = TokenService.issue_token(
            self.user, TokenType.REFRESH, timedelta(days=7)
        )
        AuthService.logout(self.user, refresh_token=jwt_str)
        self.assertEqual(
            Token.objects.filter(user=self.user, token_type=TokenType.REFRESH).count(),
            0,
        )

    def test_generate_access_token_contains_claims(self) -> None:
        """The access token should contain ``user_id`` and ``email`` claims."""
        token = AuthService.generate_access_token(self.user)
        payload = jwt.decode(token, settings.JWT_PUBLIC_KEY, algorithms=["RS256"])
        self.assertEqual(payload["user_id"], str(self.user.id))
        self.assertEqual(payload["email"], self.user.email)


class AccountServiceTest(TestCase):
    """Tests for ``AccountService``."""

    def test_register_creates_user(self) -> None:
        """Registration should create a new unverified user."""
        user = AccountService.register(email="new@test.com", password="NewPass123!")
        self.assertFalse(user.is_verified)
        self.assertEqual(user.email, "new@test.com")

    def test_register_duplicate_email(self) -> None:
        """Registering a duplicate email should raise ``UserAlreadyExistsError``."""
        AccountService.register(email="dup@test.com", password="Pass123!")
        with self.assertRaises(UserAlreadyExistsError):
            AccountService.register(email="dup@test.com", password="Pass123!")

    def test_verify_email_success(self) -> None:
        """Email verification should set ``is_verified`` to ``True``."""
        user = AccountService.register(email="verify@test.com", password="Pass123!")
        token = Token.objects.get(user=user, token_type=TokenType.EMAIL_VERIFY)
        raw_opaque = Token.generate_opaque_string()
        token.token_hash = Token.hash_token(raw_opaque)
        token.save()

        payload = {
            "user_id": str(user.id),
            "token": raw_opaque,
            "type": TokenType.EMAIL_VERIFY,
            "exp": token.expires_at,
            "iat": token.created_at,
        }
        jwt_str = jwt.encode(payload, settings.JWT_PRIVATE_KEY, algorithm="RS256")

        AccountService.verify_email(jwt_str)
        user.refresh_from_db()
        self.assertTrue(user.is_verified)

    def test_request_password_reset_nonexistent_email(self) -> None:
        """Requesting reset for nonexistent email should return ``None``."""
        result = AccountService.request_password_reset("nonexistent@test.com")
        self.assertIsNone(result)

    def test_request_password_reset_existing_user(self) -> None:
        """Requesting reset for an existing user should return a JWT string."""
        user = UserFactory()
        result = AccountService.request_password_reset(user.email)
        self.assertIsNotNone(result)


class UserMFAServiceTest(TestCase):
    """Tests for ``UserMFAService``."""

    def setUp(self) -> None:
        """Create a verified user for MFA operations."""
        self.user = UserFactory()

    def test_enroll_creates_mfa_record(self) -> None:
        """Enrollment should create a ``UserMFA`` record with ``is_enabled=False``."""
        result = UserMFAService.enroll(self.user)
        self.assertIn("secret", result)
        self.assertIn("otpauth_uri", result)
        from identity.models.mfa import UserMFA

        mfa = UserMFA.objects.get(user=self.user)
        self.assertFalse(mfa.is_enabled)

    def test_verify_and_enable_success(self) -> None:
        """Verifying with a correct OTP should enable MFA."""
        result = UserMFAService.enroll(self.user)
        raw_secret = result["secret"]
        totp = pyotp.TOTP(raw_secret)
        otp_code = totp.now()

        UserMFAService.verify_and_enable(self.user, otp_code)
        from identity.models.mfa import UserMFA

        mfa = UserMFA.objects.get(user=self.user)
        self.assertTrue(mfa.is_enabled)

    def test_verify_and_enable_wrong_otp(self) -> None:
        """Verifying with an incorrect OTP should raise ``InvalidOTPError``."""
        UserMFAService.enroll(self.user)
        with self.assertRaises(InvalidOTPError):
            UserMFAService.verify_and_enable(self.user, "000000")

    def test_verify_and_enable_no_enrollment(self) -> None:
        """Verifying without enrollment should raise ``MFAEnrollmentNotFoundError``."""
        with self.assertRaises(MFAEnrollmentNotFoundError):
            UserMFAService.verify_and_enable(self.user, "123456")

    def test_issue_challenge_no_mfa(self) -> None:
        """Issuing a challenge for a user without MFA should return ``None``."""
        result = UserMFAService.issue_challenge(self.user)
        self.assertIsNone(result)

    def test_issue_challenge_with_mfa(self) -> None:
        """Issuing a challenge for a user with MFA should return a JWT string."""
        from tests.factories import UserMFAFactory

        UserMFAFactory(user=self.user, is_enabled=True)
        result = UserMFAService.issue_challenge(self.user)
        self.assertIsNotNone(result)


class SSOServiceTest(TestCase):
    """Tests for ``SSOService``."""

    def setUp(self) -> None:
        """Create a user for SSO testing."""
        self.user = UserFactory()

    @patch("identity.services.sso_service.get_sso_service")
    def test_sso_login_existing_social_account(self, mock_get_sso: MagicMock) -> None:
        """Logging in with an existing social account should return tokens."""
        from tests.factories import SocialAccountFactory

        social = SocialAccountFactory(user=self.user, provider="GITHUB")
        mock_integration = MagicMock()
        mock_integration.exchange_code_and_get_user.return_value = (
            social.provider_user_id,
            social.provider_email,
        )
        mock_get_sso.return_value = mock_integration

        result = SSOService.login_or_register("GITHUB", "test_code")
        self.assertIn("access_token", result)
        self.assertIn("refresh_token", result)

    @patch("identity.services.sso_service.get_sso_service")
    def test_sso_register_new_user(self, mock_get_sso: MagicMock) -> None:
        """A new SSO user should be created and tokens returned."""
        mock_integration = MagicMock()
        mock_integration.exchange_code_and_get_user.return_value = (
            "99999",
            "sso_new@test.com",
        )
        mock_get_sso.return_value = mock_integration

        result = SSOService.login_or_register("GITHUB", "test_code")
        self.assertIn("access_token", result)
        new_user = User.objects.get(email="sso_new@test.com")
        self.assertTrue(new_user.is_verified)

    @patch("identity.services.sso_service.get_sso_service")
    def test_sso_email_collision_unverified(self, mock_get_sso: MagicMock) -> None:
        """SSO login colliding with an unverified local account should raise."""
        unverified = UserFactory(is_verified=False, email="collision@test.com")
        mock_integration = MagicMock()
        mock_integration.exchange_code_and_get_user.return_value = (
            "88888",
            unverified.email,
        )
        mock_get_sso.return_value = mock_integration

        with self.assertRaises(SSOEmailCollisionError):
            SSOService.login_or_register("GITHUB", "test_code")
