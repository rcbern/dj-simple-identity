# Testing Strategy

> **Section 12** of the Auth Microservice Architecture Specification. See [`README.md`](README.md) for the full index.

### Overview
Testing relies on `pytest` and `pytest-django`. The test suite mirrors the strict separation of concerns. Services are tested with mocked integrations.

### Dependencies
```text
pytest
pytest-django
pytest-mock
factory-boy
fakeredis
```

### Factories (`tests/factories.py`)
```python
import factory
from django.contrib.auth import get_user_model
User = get_user_model()

class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
    email = factory.Faker('email')
    password = factory.PostGenerationMethodCall('set_password', 'password123')
    is_active = True
    is_verified = True
```

### Test Example: Service with Mocks (`tests/test_services/test_account_service.py`)
```python
import pytest
from django.contrib.auth import get_user_model
from auth.services.account_service import AccountService

User = get_user_model()

@pytest.mark.django_db
def test_register_creates_user_and_fires_event(mocker):
    mock_publish = mocker.patch('auth.services.account_service.EventPublisher.publish')
    user = AccountService.register(email="new@test.com", password="SecurePass123!")

    assert User.objects.count() == 1
    assert user.is_verified is False

    mock_publish.assert_called_once()
    call_args = mock_publish.call_args
    # P2 FIX: Corrected positional args assertion
    assert call_args[0][0] == 'user_registered'
    assert call_args[0][1]['email'] == "new@test.com"
```

### Test Example: Infrastructure with `fakeredis`
```python
import pytest
import fakeredis
from auth.infrastructure.event_publisher import EventPublisher

@pytest.mark.django_db
def test_event_publisher_pushes_to_redis(mocker):
    fake_redis = fakeredis.FakeStrictRedis(decode_responses=True)
    mocker.patch.object(EventPublisher, '_get_client', return_value=fake_redis)

    EventPublisher.publish('user_registered', {'user_id': '123'})

    stream_data = fake_redis.xrange('auth_events')
    assert len(stream_data) == 1
    assert 'user_registered' in stream_data[0][1]['event_type']
```

## Related documents
- [Overview](overview.md)
- [Tech Stack](tech-stack.md)
- [Directory Structure](directory-structure.md)
- [Account Lifecycle & Events](domains/account-lifecycle.md)
- [Logging and Observability](observability.md)