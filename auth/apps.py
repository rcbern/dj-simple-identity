"""App configuration for the Auth Django app."""

from django.apps import AppConfig


class AuthConfig(AppConfig):
    """Configuration for the ``auth`` application.

    The directory/module path is ``auth`` but the Django app label is
    ``auth_service`` to avoid colliding with ``django.contrib.auth`` (which
    uses the label ``auth``). This keeps imports as ``auth.models.user`` and
    logger names as ``auth.*`` while satisfying Django's unique-label
    requirement.
    """

    name = "auth"
    label = "auth_service"
    verbose_name = "Authentication"
    default_auto_field = "django.db.models.BigAutoField"
