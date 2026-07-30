"""App configuration for the Identity Django app."""

from django.apps import AppConfig


class IdentityConfig(AppConfig):
    """Configuration for the ``identity`` application.

    The directory/module path is ``identity`` and the Django app label is
    also ``identity`` (no collision with ``django.contrib.auth`` which uses
    the label ``auth``).
    """

    name = "identity"
    verbose_name = "Identity & Authentication"
    default_auto_field = "django.db.models.BigAutoField"
