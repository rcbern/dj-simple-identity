"""Custom User model for the Auth microservice.

Identity is strictly tied to ``email`` — the default ``username`` and
``first_name`` fields are removed and ``PermissionsMixin`` is dropped to
eliminate unused ``groups`` and ``permissions`` tables.
"""

from __future__ import annotations

import uuid

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    """Manager for the custom ``User`` model.

    Provides ``create_user`` and ``create_superuser`` helpers that normalize
    email and hash passwords via Django's built-in hasher.
    """

    use_in_migrations = True

    def _create_user(
        self,
        email: str,
        password: str | None,
        **extra_fields: object,
    ) -> User:
        """Create and save a user with the given email and password.

        Args:
            email: The user's email address (normalized before storage).
            password: The plaintext password (hashed via ``set_password``).
            **extra_fields: Additional model fields (``is_staff``, etc.).

        Returns:
            The newly created ``User`` instance.

        Raises:
            ValueError: If ``email`` is empty.
        """
        if not email:
            raise ValueError("Users must have an email address.")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(
        self,
        email: str,
        password: str | None = None,
        **extra_fields: object,
    ) -> User:
        """Create a standard (non-admin) user.

        Args:
            email: The user's email address.
            password: The plaintext password.
            **extra_fields: Additional model fields.

        Returns:
            The newly created ``User`` instance.
        """
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        extra_fields.setdefault("is_verified", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(
        self,
        email: str,
        password: str | None = None,
        **extra_fields: object,
    ) -> User:
        """Create a superuser with staff and superuser privileges.

        Args:
            email: The superuser's email address.
            password: The plaintext password.
            **extra_fields: Additional model fields.

        Returns:
            The newly created ``User`` instance.
        """
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_verified", True)
        return self._create_user(email, password, **extra_fields)


class User(AbstractBaseUser):
    """Email-only custom user model.

    UUID primary keys prevent integer enumeration. ``password_changed_at``
    is crucial for stateless JWT invalidation — when a password changes,
    access tokens issued before that timestamp are rejected.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, db_index=True)
    password = models.CharField(max_length=128)

    is_active = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)

    date_joined = models.DateTimeField(default=timezone.now)
    password_changed_at = models.DateTimeField(auto_now_add=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []

    def has_module_perms(self, app_label: str) -> bool:
        """Required by django admin, Returns True only if is_superuser"""
        return bool(self.is_superuser)

    def has_perm(self, perm: str, obj=None) -> bool:
        """Required by django admin, Returns True only if is_superuser"""
        return bool(self.is_superuser)

    def change_password(self, new_password: str) -> None:
        """Set a new password and record the change timestamp.

        Args:
            new_password: The new plaintext password (hashed internally).
        """
        self.set_password(new_password)
        self.password_changed_at = timezone.now()
        self.save(update_fields=["password", "password_changed_at"])
