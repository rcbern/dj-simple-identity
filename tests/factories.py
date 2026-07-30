"""Factory Boy factories for test model creation.

Provides factories for ``User``, ``Token``, ``UserMFA``, and
``SocialAccount`` to simplify test setup.
"""

from __future__ import annotations

import factory
from cryptography.fernet import Fernet
from django.conf import settings

from identity.models.mfa import UserMFA
from identity.models.sso import SocialAccount
from identity.models.token import Token, TokenType
from identity.models.user import User


class UserFactory(factory.django.DjangoModelFactory):
    """Factory for creating ``User`` instances in tests."""

    class Meta:
        model = User

    email = factory.Sequence(lambda n: f"user{n}@test.com")
    password = factory.PostGenerationMethodCall("set_password", "TestPass123!")
    is_active = True
    is_verified = True
    is_staff = False
    is_superuser = False


class TokenFactory(factory.django.DjangoModelFactory):
    """Factory for creating ``Token`` instances in tests."""

    class Meta:
        model = Token

    user = factory.SubFactory(UserFactory)
    token_type = TokenType.REFRESH
    token_hash = factory.Sequence(lambda n: f"hash{n}" * 8)
    expires_at = factory.Faker("future_datetime")


class UserMFAFactory(factory.django.DjangoModelFactory):
    """Factory for creating ``UserMFA`` instances in tests."""

    class Meta:
        model = UserMFA

    user = factory.SubFactory(UserFactory)
    mfa_type = "TOTP"
    is_enabled = True

    @factory.lazy_attribute
    def secret(self) -> str:
        """Encrypt a dummy TOTP secret with Fernet.

        Returns:
            A Fernet-encrypted dummy base32 secret string.
        """
        fernet = Fernet(settings.MFA_ENCRYPTION_KEY)
        return fernet.encrypt(b"JBSWY3DPEHPK3PXP").decode("utf-8")


class SocialAccountFactory(factory.django.DjangoModelFactory):
    """Factory for creating ``SocialAccount`` instances in tests."""

    class Meta:
        model = SocialAccount

    user = factory.SubFactory(UserFactory)
    provider = "GITHUB"
    provider_user_id = factory.Sequence(lambda n: str(n))
    provider_email = factory.SelfAttribute("user.email")
