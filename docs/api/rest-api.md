# Layer: REST API (Django Ninja)

> **Section 11** of the Auth Microservice Architecture Specification. See [`README.md`](../README.md) for the full index.

### Architecture
The API layer is intentionally thin. It does not handle rate limiting (delegated to FastAPI Gateway). It manages HttpOnly cookies for refresh tokens.

### JWT Auth Dependency (`auth/api/auth.py`)
Validates the Access Token passed by the Gateway to protect internal Auth routes (like `/mfa/enroll`).

```python
import jwt
from ninja.security import HttpBearer
from ninja.errors import HttpError
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import datetime

User = get_user_model()

class JWTAuth(HttpBearer):
    def authenticate(self, request, token):
        try: payload = jwt.decode(token, settings.JWT_PUBLIC_KEY, algorithms=['RS256'])
        except jwt.PyJWTError: raise HttpError(401, "Invalid access token.")

        try: user = User.objects.get(id=payload['user_id'])
        except User.DoesNotExist: raise HttpError(401, "User not found.")

        token_pwd_time = datetime.fromisoformat(payload['pwd_changed_at']).replace(tzinfo=timezone.utc)
        if user.password_changed_at > token_pwd_time:
            raise HttpError(401, "Token invalidated due to password change.")
            
        request.user = user
        return user
```

### Router Example: Auth Routes (`auth/api/routers/auth_routes.py`)
```python
from ninja import Router
from ninja.errors import HttpError
from ..schemas.auth import LoginIn, TokenOut, RefreshOut
from ...services.auth_service import AuthService

router = Router()

@router.post("/login", response={200: TokenOut})
def login(request, payload: LoginIn):
    try:
        result = AuthService.login(payload.email, payload.password, request.request_id)
        response = router.create_response(request, result, status=200)
        
        if 'refresh_token' in result:
            response.set_cookie(
                key='refresh_token', value=result['refresh_token'],
                httponly=True, secure=True, samesite='Strict', max_age=7*24*60*60
            )
        return response
    except (ValueError, PermissionError) as e:
        raise HttpError(400, str(e))

@router.post("/refresh", response=RefreshOut)
def refresh_token(request):
    refresh_token = request.COOKIES.get('refresh_token')
    if not refresh_token: raise HttpError(401, "No refresh token provided.")
        
    try:
        result = AuthService.refresh(refresh_token, request.request_id)
        response = router.create_response(request, result, status=200)
        response.set_cookie(
            key='refresh_token', value=result['refresh_token'],
            httponly=True, secure=True, samesite='Strict', max_age=7*24*60*60
        )
        return response
    except PermissionError as e:
        response.delete_cookie('refresh_token')
        raise HttpError(401, str(e))

@router.post("/logout")
def logout(request):
    refresh_token = request.COOKIES.get('refresh_token')
    AuthService.logout(request.user, refresh_token, request.request_id)
    response = router.create_response(request, {"success": True}, status=200)
    response.delete_cookie('refresh_token')
    return response
```

### Router Example: Health Routes (`auth/api/routers/health_routes.py`)
```python
from ninja import Router
router = Router()

@router.get("/healthz")
def healthz(request):
    return {"status": "ok"}
```

## Related documents
- [Overview](../overview.md)
- [Architectural Decisions Summary](../architectural-decisions.md)
- [Directory Structure](../directory-structure.md)
- [Authentication & Sessions](../domains/authentication-and-sessions.md)
- [Multi-Factor Authentication (MFA)](../domains/mfa.md)
- [Token Management & Security](../domains/token-management.md)
- [Logging and Observability](../observability.md)