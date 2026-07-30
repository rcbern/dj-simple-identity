"""Request payload schemas for API endpoints.

Pydantic models for incoming request bodies, grouped by domain.
"""

from __future__ import annotations

from ninja import Schema


# --- Auth ---
class LoginRequest(Schema):
    """Login request payload."""

    email: str
    password: str


class RefreshRequest(Schema):
    """Refresh token rotation request payload."""

    refresh_token: str


class LogoutRequest(Schema):
    """Logout request payload."""

    refresh_token: str | None = None


class MFAVerifyRequest(Schema):
    """MFA verification during login."""

    mfa_token: str
    otp_code: str
    user_id: str


# --- Account ---
class RegisterRequest(Schema):
    """User registration request payload."""

    email: str
    password: str


class VerifyEmailRequest(Schema):
    """Email verification request payload."""

    token: str


class PasswordResetRequest(Schema):
    """Password reset request payload (step 1: request)."""

    email: str


class PasswordResetConfirmRequest(Schema):
    """Password reset confirm payload (step 2: set new password)."""

    token: str
    new_password: str


class ChangePasswordRequest(Schema):
    """Change password for an authenticated user."""

    current_password: str
    new_password: str


# --- MFA ---
class MFAEnrollRequest(Schema):
    """MFA enrollment request (empty — user is inferred from auth)."""

    pass


class MFAVerifyEnableRequest(Schema):
    """MFA verification to enable after enrollment."""

    otp_code: str


# --- SSO ---
class SSOCallbackRequest(Schema):
    """SSO OAuth callback request payload."""

    code: str
