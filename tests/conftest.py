"""Pytest configuration and shared fixtures.

Sets up the test database, fakeredis, and common fixtures used across
all test modules.
"""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import MagicMock, patch

import fakeredis
import pytest
from cryptography.fernet import Fernet
from django.conf import settings


@pytest.fixture(autouse=True)
def _fakeredis() -> Generator[MagicMock, None, None]:
    """Patch Redis with fakeredis for all tests.

    Yields:
        A MagicMock wrapping the fakeredis client.
    """
    fake_client = fakeredis.FakeRedis(decode_responses=True)
    with patch("identity.infrastructure.event_publisher.redis.Redis") as mock:
        mock.return_value = fake_client
        yield mock


@pytest.fixture(autouse=True)
def _fernet_key() -> None:
    """Ensure a valid Fernet key is set for MFA encryption in tests."""
    if not hasattr(settings, "MFA_ENCRYPTION_KEY") or not settings.MFA_ENCRYPTION_KEY:
        settings.MFA_ENCRYPTION_KEY = Fernet.generate_key()
