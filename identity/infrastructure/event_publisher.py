"""Event publisher for the Auth microservice.

Pushes JSON-encoded domain events to a Redis Stream (``auth_events``).
The Auth service does not send emails or notifications directly — it
publishes events and lets downstream consumers react.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import redis
from django.conf import settings

logger = logging.getLogger("identity.infrastructure.event_publisher")

STREAM_NAME = "auth_events"
STREAM_MAXLEN = 10000


class EventPublisher:
    """Publishes domain events to a Redis Stream.

    This class is intentionally stateless — each call to ``publish`` creates
    a short-lived Redis connection. For high-throughput scenarios a
    connection pool could be introduced, but the current event volume
    (registration, password reset, etc.) does not warrant it.
    """

    @staticmethod
    def _get_client() -> redis.Redis:
        """Create a Redis client from Django settings.

        Returns:
            A configured ``redis.Redis`` instance with ``decode_responses``.
        """
        return redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=settings.REDIS_PASSWORD,
            decode_responses=True,
        )

    @staticmethod
    def publish(event_type: str, payload: dict[str, Any]) -> None:
        """Publish a domain event to the ``auth_events`` Redis Stream.

        Args:
            event_type: The event name (e.g. ``"user_registered"``).
            payload: A JSON-serializable dict with event details.
        """
        try:
            client = EventPublisher._get_client()
            client.xadd(
                name=STREAM_NAME,
                fields={
                    "event_type": event_type,
                    "payload": json.dumps(payload),
                },
                maxlen=STREAM_MAXLEN,
                approximate=True,
            )
        except redis.RedisError as exc:
            logger.error("Failed to publish event %s: %s", event_type, exc)
        except (TypeError, ValueError) as exc:
            logger.error("Failed to serialize event %s: %s", event_type, exc)
