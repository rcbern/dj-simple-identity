# Domain: Single Sign-On (SSO)

> **Section 10** of the Auth Microservice Architecture Specification. See [`README.md`](../README.md) for the full index.

### Architecture
Uses the Dependency Inversion Principle. SSO integrations rely on Abstract Base Classes. If a user logs in with GitHub, but already has a local email/password account that is *unverified*, the service refuses to merge them, preventing account takeover.

### Model Definition: `SocialAccount` (`auth/models/sso.py`)
```python
import uuid
from django.db import models
from django.conf import settings

class Provider(models.TextChoices):
    GITHUB = 'GITHUB', 'GitHub'

class SocialAccount(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='social_accounts')
    provider = models.CharField(max_length=20, choices=Provider.choices)
    provider_user_id = models.CharField(max_length=255)
    provider_email = models.EmailField() 
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('provider', 'provider_user_id')
```

### Integration Layer (ABCs) (`auth/integrations/sso/`)
* **`base.py`**: Defines the interface `AbstractSSOService`.
* **`github.py`**: Concrete implementation that calls GitHub's API.
* **`__init__.py`**: Factory pattern that instantiates the correct provider.

```python
# auth/integrations/sso/__init__.py
from .github import GitHubSSOService
from .base import AbstractSSOService

sso_providers: dict[str, AbstractSSOService] = {
    'GITHUB': GitHubSSOService(),
}
def get_sso_service(provider_name: str) -> AbstractSSOService:
    service = sso_providers.get(provider_name.upper())
    if not service: raise ValueError(f"Unsupported SSO provider: {provider_name}")
    return service
```

### Service Definition: `SSOService` (`auth/services/sso_service.py`)
```python
from django.db import transaction
from datetime import timedelta
from ..models.user import User
from ..models.token import TokenType
from ..models.sso import SocialAccount, Provider
from .auth_service import AuthService
from .token_service import TokenService
from ..integrations.sso import get_sso_service

class SSOService:
    @staticmethod
    @transaction.atomic
    def login_or_register(provider_name, code, request_id=None):
        sso_integration = get_sso_service(provider_name)
        provider_user_id, provider_email = sso_integration.exchange_code_and_get_user(code)

        try:
            social_account = SocialAccount.objects.select_related('user').get(
                provider=provider_name, provider_user_id=provider_user_id
            )
            user = social_account.user
        except SocialAccount.DoesNotExist:
            try:
                user = User.objects.get(email=provider_email)
                # Collision Protection: Block merge if local account is unverified
                if not user.is_verified:
                    raise PermissionError("An account with this email exists but is not verified. Please log in with your password to verify and link accounts.")
            except User.DoesNotExist:
                user = User.objects.create_user(
                    email=provider_email, is_verified=True, password=None
                )
            
            SocialAccount.objects.create(
                user=user, provider=provider_name,
                provider_user_id=provider_user_id, provider_email=provider_email
            )

        access_token = AuthService.generate_access_token(user)
        refresh_token = TokenService.issue_token(user, TokenType.REFRESH, timedelta(days=7))
        return {'access_token': access_token, 'refresh_token': refresh_token, 'user_id': str(user.id)}
```

## Related documents
- [Overview](../overview.md)
- [Architectural Decisions Summary](../architectural-decisions.md)
- [Directory Structure](../directory-structure.md)
- [Identity & Users](identity-and-users.md)
- [Token Management & Security](token-management.md)
- [Authentication & Sessions](authentication-and-sessions.md)