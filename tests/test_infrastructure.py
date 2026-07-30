"""Unit tests for the infrastructure layer.

Covers ``EventPublisher`` — verifies that events are published to the
Redis Stream and that failures are handled gracefully.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import redis
from django.test import TestCase

from identity.infrastructure.event_publisher import EventPublisher


class EventPublisherTest(TestCase):
    """Tests for ``EventPublisher``."""

    @patch("identity.infrastructure.event_publisher.redis.Redis")
    def test_publish_success(self, mock_redis_cls: MagicMock) -> None:
        """Publishing an event should call ``xadd`` with correct fields."""
        mock_client = MagicMock()
        mock_redis_cls.return_value = mock_client

        EventPublisher.publish(
            "user_registered",
            {"user_id": "123", "email": "test@test.com"},
        )

        mock_client.xadd.assert_called_once()
        call_args = mock_client.xadd.call_args
        self.assertEqual(call_args.kwargs["name"], "auth_events")
        fields = call_args.kwargs["fields"]
        self.assertEqual(fields["event_type"], "user_registered")
        payload = json.loads(fields["payload"])
        self.assertEqual(payload["email"], "test@test.com")

    @patch("identity.infrastructure.event_publisher.redis.Redis")
    def test_publish_redis_error_handled(self, mock_redis_cls: MagicMock) -> None:
        """A Redis error should be caught and logged, not raised."""
        mock_client = MagicMock()
        mock_client.xadd.side_effect = redis.RedisError("Connection failed")
        mock_redis_cls.return_value = mock_client

        # Should not raise
        EventPublisher.publish("test_event", {"key": "value"})

    @patch("identity.infrastructure.event_publisher.redis.Redis")
    def test_publish_serialization_error_handled(
        self, mock_redis_cls: MagicMock
    ) -> None:
        """A serialization error should be caught and logged, not raised."""
        mock_client = MagicMock()
        mock_redis_cls.return_value = mock_client

        # Should not raise — non-serializable object
        EventPublisher.publish("test_event", {"bad": object()})
