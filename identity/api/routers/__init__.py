"""NinjaAPI instance and router registration.

All routers are mounted under a single ``NinjaAPI`` instance, which is
imported by ``config/urls.py`` and served at ``/api/``.
"""

from __future__ import annotations

from ninja import NinjaAPI

from identity.api.routers.account import router as account_router
from identity.api.routers.auth import router as auth_router
from identity.api.routers.mfa import router as mfa_router
from identity.api.routers.sso import router as sso_router

api = NinjaAPI(title="Auth Service API", version="0.0.1")

api.add_router("/auth", auth_router)
api.add_router("/account", account_router)
api.add_router("/mfa", mfa_router)
api.add_router("/sso", sso_router)
