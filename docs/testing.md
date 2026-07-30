# Testing Strategy

> **Section 12** of the Auth Microservice Architecture Specification. See [`README.md`](README.md) for the full index.

### Overview
Testing relies on `pytest` and `pytest-django`. The test suite mirrors the strict separation of concerns. Services are tested with mocked integrations. API integration tests use the NinjaAPI `TestClient`.

### Dependencies
```text
pytest
pytest-django
pytest-mock
factory-boy
fakeredis
```

### Configuration (`pyproject.toml`)
```toml
[tool.pytest.ini_options]
DJANGO_SETTINGS_MODULE = "config.settings"
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
```

### Shared Fixtures (`tests/conftest.py`)
An autouse fixture patches Redis with `fakeredis` for all tests. A second autouse fixture ensures a valid Fernet key is set for MFA encryption.

```python
# tests/conftest.py
import fakeredis
import pytest
from cryptography.fernet import Fernet
from django.conf import settings
from unittest.mock import patch


@pytest.fixture(autouse=True)
def _fakeredis():
    fake_client = fakeredis.FakeRedis(decode_responses=True)
    with patch("identity.infrastructure.event_publisher.redis.Redis") as mock:
        mock.return_value = fake_client
        yield mock


@pytest.fixture(autouse=True)
def _fernet_key():
    if not hasattr(settings, "MFA_ENCRYPTION_KEY") or not settings.MFA_ENCRYPTION_KEY:
        settings.MFA_ENCRYPTION_KEY = Fernet.generate_key()
```

### Factories (`tests/factories.py`)
```python
# tests/factories.py
import factory
from cryptography.fernet import Fernet
from django.conf import settings

from identity.models.mfa import UserMFA
from identity.models.sso import SocialAccount
from identity.models.token import Token, TokenType
from identity.models.user import User


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    email = factory.Sequence(lambda n: f"user{n}@test.com")
    password = factory.PostGenerationMethodCall("set_password", "TestPass123!")
    is_active = True
    is_verified = True


class TokenFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Token

    user = factory.SubFactory(UserFactory)
    token_type = TokenType.REFRESH
    token_hash = factory.Sequence(lambda n: f"hash{n}" * 8)
    expires_at = factory.Faker("future_datetime")


class UserMFAFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = UserMFA

    user = factory.SubFactory(UserFactory)
    mfa_type = "TOTP"
    is_enabled = True

    @factory.lazy_attribute
    def secret(self) -> str:
        fernet = Fernet(settings.MFA_ENCRYPTION_KEY)
        return fernet.encrypt(b"JBSWY3DPEHPK3PXP").decode("utf-8")


class SocialAccountFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SocialAccount

    user = factory.SubFactory(UserFactory)
    provider = "GITHUB"
    provider_user_id = factory.Sequence(lambda n: str(n))
    provider_email = factory.SelfAttribute("user.email")
```

### Test Example: Service Tests (`tests/test_services.py`)
Service tests use `TestCase` and factory-boy to create users. SSO tests mock the integration layer.

```python
# tests/test_services.py (excerpt)
from django.test import TestCase
from identity.services.auth_service import AuthService
from tests.factories import UserFactory


class AuthServiceTest(TestCase):
    def setUp(self):
        self.user = UserFactory(password="TestPass123!")

    def test_login_success(self):
        result = AuthService.login(
            email=self.user.email, password="TestPass123!"
        )
        self.assertIn("access_token", result)
        self.assertIn("refresh_token", result)
```

### Test Example: Infrastructure Tests (`tests/test_infrastructure.py`)
```python
# tests/test_infrastructure.py (excerpt)
from unittest.mock import MagicMock, patch
from django.test import TestCase
from identity.infrastructure.event_publisher import EventPublisher


class EventPublisherTest(TestCase):
    @patch("identity.infrastructure.event_publisher.redis.Redis")
    def test_publish_success(self, mock_redis_cls):
        mock_client = MagicMock()
        mock_redis_cls.return_value = mock_client

        EventPublisher.publish("user_registered", {"user_id": "123"})

        mock_client.xadd.assert_called_once()
```

### Test Example: API Integration Tests (`tests/test_api.py`)
API tests use `ninja.testing.TestClient` to exercise the full request/response cycle.

```python
# tests/test_api.py (excerpt)
from django.test import TestCase
from ninja.testing import TestClient
from identity.api.routers import api
from tests.factories import UserFactory


class AuthAPITest(TestCase):
    def setUp(self):
        super().setUp()
        self.client = TestClient(api)
        self.user = UserFactory(password="TestPass123!")

    def test_login_success(self):
        response = self.client.post(
            "/auth/login",
            json={"email": self.user.email, "password": "TestPass123!"},
        )
        self.assertEqual(response.status_code, 200)
```

## Related documents
- [Overview](overview.md)
- [Tech Stack](tech-stack.md)
- [Directory Structure](directory-structure.md)
- [Account Lifecycle & Events](domains/account-lifecycle.md)
- [Logging and Observability](observability.md)