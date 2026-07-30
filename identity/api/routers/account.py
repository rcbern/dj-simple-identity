"""Account API router — register, verify email, password reset, change password.

Registration and password reset request are public. Email verification
and password reset confirm are public (token-based). Change password
requires JWT auth.
"""

from __future__ import annotations

from django.http import HttpRequest
from ninja import Router

from identity.api.auth import JWTAuth
from identity.api.schemas.common import Error, Message
from identity.api.schemas.requests import (
    ChangePasswordRequest,
    PasswordResetConfirmRequest,
    PasswordResetRequest,
    RegisterRequest,
    VerifyEmailRequest,
)
from identity.exceptions import AuthError, TokenInvalidError, UserAlreadyExistsError
from identity.services.account_service import AccountService

router = Router(tags=["account"])


@router.post(
    "/register",
    response={201: Message, 409: Error},
)
def register(request: HttpRequest, payload: RegisterRequest):
    """Register a new user account."""
    try:
        AccountService.register(
            email=payload.email,
            password=payload.password,
            request_id=getattr(request, "request_id", None),
        )
    except UserAlreadyExistsError as exc:
        return 409, Error(detail=str(exc))
    return 201, Message(message="Registration successful. Check your email.")


@router.post(
    "/verify-email",
    response={200: Message, 401: Error},
)
def verify_email(request: HttpRequest, payload: VerifyEmailRequest):
    """Verify a user's email address with a verification token."""
    try:
        AccountService.verify_email(
            verify_token=payload.token,
            request_id=getattr(request, "request_id", None),
        )
    except TokenInvalidError as exc:
        return 401, Error(detail=str(exc))
    return 200, Message(message="Email verified successfully.")


@router.post(
    "/password-reset/request",
    response={200: Message},
)
def request_password_reset(request: HttpRequest, payload: PasswordResetRequest):
    """Request a password reset token (always returns 200 to prevent enumeration)."""
    AccountService.request_password_reset(
        email=payload.email,
        request_id=getattr(request, "request_id", None),
    )
    return 200, Message(
        message="If an account exists with this email, a reset link has been sent."
    )


@router.post(
    "/password-reset/confirm",
    response={200: Message, 401: Error},
)
def confirm_password_reset(request: HttpRequest, payload: PasswordResetConfirmRequest):
    """Reset a user's password using a reset token."""
    try:
        AccountService.confirm_password_reset(
            reset_token=payload.token,
            new_password=payload.new_password,
            request_id=getattr(request, "request_id", None),
        )
    except TokenInvalidError as exc:
        return 401, Error(detail=str(exc))
    return 200, Message(message="Password reset successfully.")


@router.post(
    "/change-password",
    response={200: Message, 401: Error},
    auth=JWTAuth(),
)
def change_password(request: HttpRequest, payload: ChangePasswordRequest):
    """Change the authenticated user's password."""
    user = request.auth
    try:
        user.change_password(payload.new_password)
    except AuthError as exc:
        return 401, Error(detail=str(exc))
    return 200, Message(message="Password changed successfully.")
