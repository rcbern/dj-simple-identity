# Layer: REST API (Django Ninja)

> **Section 11** of the Auth Microservice Architecture Specification. See [`README.md`](../README.md) for the full index.

### Architecture
The API layer is intentionally thin. It does not handle rate limiting (delegated to FastAPI Gateway). Refresh tokens are returned in the JSON response body (not HttpOnly cookies) — the gateway or client is responsible for secure storage.

### JWT Auth Dependency (`identity/api/auth.py`)
Validates the RS256 Access Token passed by the Gateway to protect internal Auth routes (like `/mfa/enroll`). Returns `None` on failure (Django Ninja converts this to a 401 response).

```python
# identity/api/auth.py
import logging
from datetime import UTC, datetime

import jwt
from django.conf import settings
from django.contrib.auth import get_user_model
from ninja.security import HttpBearer

logger = logging.getLogger("identity.api.auth")
UserModel = get_user_model()


class JWTAuth(HttpBearer):
    def authenticate(self, request, token: str):
        try:
            payload = jwt.decode(token, settings.JWT_PUBLIC_KEY, algorithms=["RS256"])
        except jwt.PyJWTError:
            logger.warning("Invalid JWT received")
            return None

        exp = payload.get("exp")
        if exp and datetime.now(UTC).timestamp() > exp:
            logger.warning("Expired JWT received")
            return None

        user_id = payload.get("user_id")
        if not user_id:
            return None

        try:
            return UserModel.objects.get(id=user_id)
        except UserModel.DoesNotExist:
            logger.warning("JWT user not found: %s", user_id)
            return None
```

### Schemas (`identity/api/schemas/`)
Pydantic models for request/response payloads, split into `common.py` (Error, Message, TokenPair, MFAChallenge) and `requests.py` (per-domain request bodies).

### Routers (`identity/api/routers/`)
All routers are mounted under a single `NinjaAPI` instance served at `/api/`.

#### Auth Router (`identity/api/routers/auth.py`)
* `POST /auth/login` — Authenticate, return tokens or MFA challenge
* `POST /auth/mfa/verify` — Verify MFA challenge and issue tokens
* `POST /auth/refresh` — Rotate refresh token
* `POST /auth/logout` — Revoke refresh token (requires JWT auth)

```python
# identity/api/routers/auth.py (excerpt)
@router.post("/login", response={200: TokenPair | MFAChallenge, 401: Error})
def login(request, payload: LoginRequest):
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


@router.post("/logout", response={200: Message, 401: Error}, auth=JWTAuth())
def logout(request, payload: LogoutRequest):
    user = request.auth
    AuthService.logout(user=user, refresh_token=payload.refresh_token)
    return 200, Message(message="Logged out successfully.")
```

#### Account Router (`identity/api/routers/account.py`)
* `POST /account/register` — Register a new user (public)
* `POST /account/verify-email` — Verify email with token (public)
* `POST /account/password-reset/request` — Request reset token (public, always 200)
* `POST /account/password-reset/confirm` — Reset password with token (public)
* `POST /account/change-password` — Change password (requires JWT auth)

#### MFA Router (`identity/api/routers/mfa.py`)
* `POST /mfa/enroll` — Generate TOTP secret (requires JWT auth)
* `POST /mfa/verify` — Verify OTP and enable MFA (requires JWT auth)

#### SSO Router (`identity/api/routers/sso.py`)
* `POST /sso/{provider}/callback` — Handle OAuth callback (public)

### NinjaAPI Instance (`identity/api/routers/__init__.py`)
```python
# identity/api/routers/__init__.py
from ninja import NinjaAPI

from identity.api.routers.account import router as account_router
from identity.api.routers.auth import router as auth_router
from identity.api.routers.mfa import router as mfa_router
from identity.api.routers.sso import router as sso_router

api = NinjaAPI(title="Auth Service API", version="0.1.0")

api.add_router("/auth", auth_router)
api.add_router("/account", account_router)
api.add_router("/mfa", mfa_router)
api.add_router("/sso", sso_router)
```

## Related documents
- [Overview](../overview.md)
- [Architectural Decisions Summary](../architectural-decisions.md)
- [Directory Structure](../directory-structure.md)
- [Authentication & Sessions](../domains/authentication-and-sessions.md)
- [Multi-Factor Authentication (MFA)](../domains/mfa.md)
- [Token Management & Security](../domains/token-management.md)
- [Logging and Observability](../observability.md)