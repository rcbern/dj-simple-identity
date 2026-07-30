"""Middleware for the Auth API.

Provides request-id correlation for structured logging across all layers.
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Callable

from django.http import HttpRequest, HttpResponse

logger = logging.getLogger("identity.middleware")


class RequestIDMiddleware:
    """Assign or propagate an ``X-Request-ID`` for every request.

    The request-id is attached to ``request.request_id`` and echoed back in
    the response header. Services receive it explicitly as a function
    argument (no ``contextvars``) to keep signatures transparent.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        """Store the next handler in the chain.

        Args:
            get_response: The next middleware or view callable.
        """
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """Process an incoming request and attach a correlation id.

        Args:
            request: The incoming Django ``HttpRequest``.

        Returns:
            The outgoing ``HttpResponse`` with ``X-Request-ID`` set.
        """
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.request_id = request_id
        logger.info(
            "Incoming request: %s %s",
            request.method,
            request.path,
            extra={"request_id": request_id},
        )

        response = self.get_response(request)
        response["X-Request-ID"] = request_id
        return response
