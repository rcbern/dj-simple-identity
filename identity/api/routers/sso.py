"""SSO API router — OAuth callback for social login.

Public endpoint — the provider's authorization code is exchanged for
tokens without prior JWT auth.
"""

from __future__ import annotations

from django.http import HttpRequest
from ninja import Router

from identity.api.schemas.common import Error, TokenPair
from identity.api.schemas.requests import SSOCallbackRequest
from identity.exceptions import SSOError
from identity.services.sso_service import SSOService

router = Router(tags=["sso"])


@router.post(
    "/{provider}/callback",
    response={200: TokenPair, 401: Error},
)
def sso_callback(
    request: HttpRequest,
    provider: str,
    payload: SSOCallbackRequest,
):
    """Handle an SSO OAuth callback and return tokens."""
    try:
        result = SSOService.login_or_register(
            provider_name=provider.upper(),
            code=payload.code,
            request_id=getattr(request, "request_id", None),
        )
    except SSOError as exc:
        return 401, Error(detail=str(exc))
    return 200, TokenPair(
        access_token=result["access_token"],
        refresh_token=result["refresh_token"],
        user_id=result["user_id"],
    )
