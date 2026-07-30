"""Root URL configuration for the Auth microservice.

Mounts the Django Ninja API under ``/api`` and the Django admin under
``/admin``.
"""

from django.contrib import admin
from django.urls import path

from identity.api.routers import api

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", api.urls),
]
