# Domain: Single Sign-On (SSO)

> **Section 7** of the Auth Microservice Architecture Specification. See [`README.md`](../README.md) for the full index.

### Architecture
Uses the Dependency Inversion Principle. SSO integrations rely on Abstract Base Classes. If a user logs in with GitHub, but already has a local email/password account that is *unverified*, the service refuses to merge them, preventing account takeover.

### Model Definition: `SocialAccount` (`identity/models/sso.py`)
```python
# identity/models/sso.py
import uuid

from django.conf import settings
from django.db import models


class Provider(models.TextChoices):
    GITHUB = "GITHUB", "GitHub"


class SocialAccount(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="social_accounts",
    )
    provider = models.CharField(max_length=20, choices=Provider.choices)
    provider_user_id = models.CharField(max_length=255)
    provider_email = models.EmailField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("provider", "provider_user_id")
```

### Integration Layer (ABCs) (`identity/integrations/sso/`)
* **`base.py`**: Defines the interface `AbstractSSOService`.
* **`github.py`**: Concrete implementation that calls GitHub's API.
* **`__init__.py`**: Factory pattern that instantiates the correct provider.

```python
# identity/integrations/sso/__init__.py
from identity.integrations.sso.base import AbstractSSOService
from identity.integrations.sso.github import GitHubSSOService

sso_providers: dict[str, AbstractSSOService] = {
    "GITHUB": GitHubSSOService(),
}


def get_sso_service(provider_name: str) -> AbstractSSOService:
    service = sso_providers.get(provider_name.upper())
    if not service:
        raise ValueError(f"Unsupported SSO provider: {provider_name}")
    return service
```

### Service Definition: `SSOService` (`identity/services/sso_service.py`)
Uses `SSOEmailCollisionError` instead of bare `PermissionError` for email collision protection.

```python
# identity/services/sso_service.py
import logging
from datetime import timedelta
from typing import Any

from django.db import transaction

from identity.exceptions import SSOEmailCollisionError
from identity.integrations.sso import get_sso_service
from identity.models.sso import SocialAccount
from identity.models.token import TokenType
from identity.models.user import User
from identity.services.auth_service import AuthService
from identity.services.token_service import TokenService

logger = logging.getLogger("identity.services.sso_service")

REFRESH_TOKEN_EXPIRY_DAYS = 7


class SSOService:
    @staticmethod
    @transaction.atomic
    def login_or_register(
        provider_name: str, code: str, request_id: str | None = None
    ) -> dict[str, Any]:
        sso_integration = get_sso_service(provider_name)
        provider_user_id, provider_email = sso_integration.exchange_code_and_get_user(
            code
        )

        try:
            social_account = SocialAccount.objects.select_related("user").get(
                provider=provider_name, provider_user_id=provider_user_id
            )
            user = social_account.user
        except SocialAccount.DoesNotExist:
            try:
                user = User.objects.get(email=provider_email)
                # Collision Protection: Block merge if local account is unverified
                if not user.is_verified:
                    raise SSOEmailCollisionError(
                        "An account with this email exists but is not "
                        "verified. Please log in with your password to "
                        "verify and link accounts."
                    )
            except User.DoesNotExist:
                user = User.objects.create_user(
                    email=provider_email, is_verified=True, password=None
                )

            SocialAccount.objects.create(
                user=user,
                provider=provider_name,
                provider_user_id=provider_user_id,
                provider_email=provider_email,
            )

        access_token = AuthService.generate_access_token(user)
        refresh_token = TokenService.issue_token(
            user, TokenType.REFRESH, timedelta(days=REFRESH_TOKEN_EXPIRY_DAYS)
        )
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user_id": str(user.id),
        }
```

## Related documents
- [Overview](../overview.md)
- [Identity & Users](identity-and-users.md)
- [Token Management & Security](token-management.md)
- [Authentication & Sessions](authentication-and-sessions.md)
