"""Common API schemas shared across endpoints.

Pydantic models for request/response payloads used by the API routers.
"""

from __future__ import annotations

from uuid import UUID

from ninja import Schema


class Error(Schema):
    """Standard error response schema."""

    detail: str


class Message(Schema):
    """Generic message response schema."""

    message: str


class TokenPair(Schema):
    """Access + refresh token pair response."""

    access_token: str
    refresh_token: str
    user_id: UUID


class MFAChallenge(Schema):
    """MFA challenge response during login."""

    mfa_required: bool
    mfa_token: str
    user_id: UUID
