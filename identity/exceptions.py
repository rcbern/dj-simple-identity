"""Custom domain exceptions for the Auth microservice.

These replace bare ``ValueError`` and ``PermissionError`` with
semantically meaningful exception types, making error handling in the
API layer cleaner and more explicit.
"""

from __future__ import annotations


class AuthError(Exception):
    """Base exception for all Auth domain errors."""


class InvalidCredentialsError(AuthError):
    """Raised when login credentials do not match."""


class EmailNotVerifiedError(AuthError):
    """Raised when a user attempts to log in without verifying their email."""


class UserAlreadyExistsError(AuthError):
    """Raised when attempting to register a duplicate email."""


class TokenInvalidError(AuthError):
    """Raised when a token is invalid, expired, or not found."""


class MFAError(AuthError):
    """Base exception for MFA-related errors."""


class MFAEnrollmentNotFoundError(MFAError):
    """Raised when MFA verification is attempted without prior enrollment."""


class MFANotEnabledError(MFAError):
    """Raised when an MFA challenge is issued/verified for a user without MFA."""


class InvalidOTPError(MFAError):
    """Raised when the submitted OTP code does not match."""


class MFAChallengeInvalidError(MFAError):
    """Raised when the MFA challenge token is invalid or expired."""


class SSOError(AuthError):
    """Base exception for SSO-related errors."""


class UnsupportedSSOProviderError(SSOError):
    """Raised when an unsupported SSO provider is requested."""


class SSOEmailCollisionError(SSOError):
    """Raised when a social login collides with an unverified local account."""
