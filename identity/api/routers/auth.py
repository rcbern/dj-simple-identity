"""Auth API router — login, logout, refresh, MFA verify.

All endpoints are public (no JWT auth) except logout which requires auth.
"""

from __future__ import annotations

from datetime import timedelta

from django.http import HttpRequest
from ninja import Router

from identity.api.auth import JWTAuth
from identity.api.schemas.common import Error, Message, MFAChallenge, TokenPair
from identity.api.schemas.requests import (
    LoginRequest,
    LogoutRequest,
    MFAVerifyRequest,
    RefreshRequest,
)
from identity.exceptions import (
    AuthError,
    InvalidOTPError,
    MFAChallengeInvalidError,
    MFANotEnabledError,
    TokenInvalidError,
)
from identity.models.token import TokenType
from identity.models.user import User
from identity.services.auth_service import AuthService
from identity.services.mfa_service import UserMFAService
from identity.services.token_service import TokenService

router = Router(tags=["auth"])


@router.post(
    "/login",
    response={200: TokenPair | MFAChallenge, 401: Error},
)
def login(request: HttpRequest, payload: LoginRequest):
    """Authenticate a user and return tokens or an MFA challenge."""
    try:
        result = AuthService.login(
            email=payload.email,
            password=payload.password,
            request_id=getattr(request, "request_id", None),
        )
        if result.get("mfa_required"):
            return 200, MFAChallenge(
                mfa_required=True,
                mfa_token=result["mfa_token"],
                user_id=result["user_id"],
            )
        return 200, TokenPair(
            access_token=result["access_token"],
            refresh_token=result["refresh_token"],
            user_id=result["user_id"],
        )
    except AuthError as exc:
        return 401, Error(detail=str(exc))


@router.post(
    "/mfa/verify",
    response={200: TokenPair, 401: Error},
)
def mfa_verify(request: HttpRequest, payload: MFAVerifyRequest):
    """Verify an MFA challenge and issue tokens."""
    try:
        user = User.objects.get(id=payload.user_id)
    except User.DoesNotExist:
        return 401, Error(detail="User not found.")

    try:
        UserMFAService.verify_challenge(
            user=user,
            otp_code=payload.otp_code,
            challenge_token=payload.mfa_token,
        )
    except (InvalidOTPError, MFAChallengeInvalidError, MFANotEnabledError) as exc:
        return 401, Error(detail=str(exc))

    access_token = AuthService.generate_access_token(user)
    refresh_token = TokenService.issue_token(user, TokenType.REFRESH, timedelta(days=7))
    return 200, TokenPair(
        access_token=access_token,
        refresh_token=refresh_token,
        user_id=user.id,
    )


@router.post(
    "/refresh",
    response={200: TokenPair, 401: Error},
)
def refresh(request: HttpRequest, payload: RefreshRequest):
    """Rotate a refresh token and return a new token pair."""
    try:
        result = AuthService.refresh(
            raw_refresh_token=payload.refresh_token,
            request_id=getattr(request, "request_id", None),
        )
        return 200, TokenPair(
            access_token=result["access_token"],
            refresh_token=result["refresh_token"],
            user_id=result.get("user_id", ""),
        )
    except TokenInvalidError as exc:
        return 401, Error(detail=str(exc))


@router.post(
    "/logout",
    response={200: Message, 401: Error},
    auth=JWTAuth(),
)
def logout(request: HttpRequest, payload: LogoutRequest):
    """Log out the authenticated user by deleting their refresh token."""
    user = request.auth
    AuthService.logout(
        user=user,
        refresh_token=payload.refresh_token,
        request_id=getattr(request, "request_id", None),
    )
    return 200, Message(message="Logged out successfully.")
