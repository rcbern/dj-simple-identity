"""Schema re-exports for the API layer."""

from identity.api.schemas.common import Error, Message, MFAChallenge, TokenPair
from identity.api.schemas.requests import (
    ChangePasswordRequest,
    LoginRequest,
    LogoutRequest,
    MFAEnrollRequest,
    MFAVerifyEnableRequest,
    MFAVerifyRequest,
    PasswordResetConfirmRequest,
    PasswordResetRequest,
    RefreshRequest,
    RegisterRequest,
    SSOCallbackRequest,
    VerifyEmailRequest,
)

__all__ = [
    "ChangePasswordRequest",
    "Error",
    "LoginRequest",
    "LogoutRequest",
    "MFAChallenge",
    "MFAEnrollRequest",
    "MFAVerifyEnableRequest",
    "MFAVerifyRequest",
    "Message",
    "PasswordResetConfirmRequest",
    "PasswordResetRequest",
    "RefreshRequest",
    "RegisterRequest",
    "SSOCallbackRequest",
    "TokenPair",
    "VerifyEmailRequest",
]
