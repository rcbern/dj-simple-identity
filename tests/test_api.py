"""Integration tests for the API layer.

Tests the NinjaAPI endpoints via Django's test client, covering auth,
account, MFA, and SSO routers.
"""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import MagicMock, patch

from django.test import TestCase
from ninja.testing import TestClient

from identity.api.routers import api
from identity.exceptions import SSOError
from identity.models.token import TokenType
from identity.services.auth_service import AuthService
from identity.services.token_service import TokenService
from tests.factories import UserFactory


class APITestBase(TestCase):
    """Base class providing the NinjaAPI test client."""

    def setUp(self) -> None:
        """Initialize the NinjaAPI test client."""
        super().setUp()
        self.client = TestClient(api)


class AuthAPITest(APITestBase):
    """Tests for the auth API router."""

    def setUp(self) -> None:
        """Create a verified user for login tests."""
        super().setUp()
        self.user = UserFactory(password="TestPass123!")

    def test_login_success(self) -> None:
        """POST /auth/login with valid credentials should return 200."""
        response = self.client.post(
            "/auth/login",
            json={"email": self.user.email, "password": "TestPass123!"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("access_token", data)
        self.assertIn("refresh_token", data)

    def test_login_invalid_credentials(self) -> None:
        """POST /auth/login with wrong password should return 401."""
        response = self.client.post(
            "/auth/login",
            json={"email": self.user.email, "password": "WrongPass!"},
        )
        self.assertEqual(response.status_code, 401)

    def test_refresh_success(self) -> None:
        """POST /auth/refresh with a valid token should return 200."""
        jwt_str = TokenService.issue_token(
            self.user, TokenType.REFRESH, timedelta(days=7)
        )
        response = self.client.post(
            "/auth/refresh",
            json={"refresh_token": jwt_str},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("access_token", data)
        self.assertIn("refresh_token", data)

    def test_refresh_invalid_token(self) -> None:
        """POST /auth/refresh with an invalid token should return 401."""
        response = self.client.post(
            "/auth/refresh",
            json={"refresh_token": "invalid.jwt.string"},
        )
        self.assertEqual(response.status_code, 401)

    def test_logout_requires_auth(self) -> None:
        """POST /auth/logout without a JWT should return 401."""
        response = self.client.post(
            "/auth/logout",
            json={"refresh_token": None},
        )
        self.assertEqual(response.status_code, 401)

    def test_logout_with_auth(self) -> None:
        """POST /auth/logout with a valid JWT should return 200."""
        access_token = AuthService.generate_access_token(self.user)
        response = self.client.post(
            "/auth/logout",
            json={"refresh_token": None},
            headers={"Authorization": f"Bearer {access_token}"},
        )
        self.assertEqual(response.status_code, 200)


class AccountAPITest(APITestBase):
    """Tests for the account API router."""

    def test_register_success(self) -> None:
        """POST /account/register with a new email should return 201."""
        response = self.client.post(
            "/account/register",
            json={"email": "newapi@test.com", "password": "NewPass123!"},
        )
        self.assertEqual(response.status_code, 201)

    def test_register_duplicate(self) -> None:
        """POST /account/register with a duplicate email should return 409."""
        self.client.post(
            "/account/register",
            json={"email": "dup@test.com", "password": "Pass123!"},
        )
        response = self.client.post(
            "/account/register",
            json={"email": "dup@test.com", "password": "Pass123!"},
        )
        self.assertEqual(response.status_code, 409)

    def test_password_reset_request_always_200(self) -> None:
        """POST /account/password-reset/request should always return 200."""
        response = self.client.post(
            "/account/password-reset/request",
            json={"email": "nonexistent@test.com"},
        )
        self.assertEqual(response.status_code, 200)


class MFAAPITest(APITestBase):
    """Tests for the MFA API router."""

    def setUp(self) -> None:
        """Create a verified user and generate an access token."""
        super().setUp()
        self.user = UserFactory(password="TestPass123!")
        self.access_token = AuthService.generate_access_token(self.user)

    def test_enroll_requires_auth(self) -> None:
        """POST /mfa/enroll without a JWT should return 401."""
        response = self.client.post("/mfa/enroll", json={})
        self.assertEqual(response.status_code, 401)

    def test_enroll_success(self) -> None:
        """POST /mfa/enroll with a valid JWT should return 200."""
        response = self.client.post(
            "/mfa/enroll",
            json={},
            headers={"Authorization": f"Bearer {self.access_token}"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("secret", data)
        self.assertIn("otpauth_uri", data)


class SSOAPITest(APITestBase):
    """Tests for the SSO API router."""

    @patch("identity.services.sso_service.get_sso_service")
    def test_sso_callback_success(self, mock_get_sso: MagicMock) -> None:
        """POST /sso/{provider}/callback should return 200 with tokens."""
        mock_integration = MagicMock()
        mock_integration.exchange_code_and_get_user.return_value = (
            "12345",
            "ssotest@test.com",
        )
        mock_get_sso.return_value = mock_integration

        response = self.client.post(
            "/sso/github/callback",
            json={"code": "test_code"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("access_token", data)
        self.assertIn("refresh_token", data)

    @patch("identity.services.sso_service.get_sso_service")
    def test_sso_callback_error(self, mock_get_sso: MagicMock) -> None:
        """POST /sso/{provider}/callback with an SSO error should return 401."""
        mock_integration = MagicMock()
        mock_integration.exchange_code_and_get_user.side_effect = SSOError(
            "OAuth failed"
        )
        mock_get_sso.return_value = mock_integration

        response = self.client.post(
            "/sso/github/callback",
            json={"code": "bad_code"},
        )
        self.assertEqual(response.status_code, 401)
