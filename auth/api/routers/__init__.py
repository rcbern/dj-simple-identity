"""Django Ninja API instance and router registration.

All routers are registered here and the single ``api`` instance is mounted
in ``config/urls.py`` under ``/api``.
"""

from __future__ import annotations

from ninja import NinjaAPI

api = NinjaAPI(title="Auth Service API", version="0.1.0")

# Routers will be registered here as they are implemented in Phase 6.
