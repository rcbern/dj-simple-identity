"""MFA API router — enroll, verify/enable, status.

All endpoints require JWT auth.
"""

from __future__ import annotations

from django.http import HttpRequest
from ninja import Router, Schema

from identity.api.auth import JWTAuth
from identity.api.schemas.common import Error, Message
from identity.api.schemas.requests import MFAVerifyEnableRequest
from identity.exceptions import MFAError
from identity.services.mfa_service import UserMFAService

router = Router(tags=["mfa"])


class MFAEnrollResponse(Schema):
    """Response schema for MFA enrollment."""

    secret: str
    otpauth_uri: str


@router.post(
    "/enroll",
    response={200: MFAEnrollResponse, 401: Error},
    auth=JWTAuth(),
)
def mfa_enroll(request: HttpRequest):
    """Enroll the authenticated user in MFA (generates TOTP secret)."""
    user = request.auth
    result = UserMFAService.enroll(user)
    return 200, MFAEnrollResponse(
        secret=result["secret"], otpauth_uri=result["otpauth_uri"]
    )


@router.post(
    "/verify",
    response={200: Message, 401: Error},
    auth=JWTAuth(),
)
def mfa_verify_enable(request: HttpRequest, payload: MFAVerifyEnableRequest):
    """Verify an OTP code and enable MFA for the authenticated user."""
    user = request.auth
    try:
        UserMFAService.verify_and_enable(user=user, otp_code=payload.otp_code)
    except MFAError as exc:
        return 401, Error(detail=str(exc))
    return 200, Message(message="MFA enabled successfully.")
