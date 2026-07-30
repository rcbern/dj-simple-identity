# Domain: Identity & Users

> **Section 2** of the Auth Microservice Architecture Specification. See [`README.md`](../README.md) for the full index.

### Architecture
The `User` model strips away default Django fields (`first_name`, `username`) and drops `PermissionsMixin` (removing unused `groups` and `permissions` tables). Identity is strictly tied to `email`.

### Model Definition: `User` (`identity/models/user.py`)
* **`id`**: UUID Primary Key. Prevents integer enumeration.
* **`email`**: Unique, indexed. Used as the `USERNAME_FIELD`.
* **`password`**: Handled by Django's built-in hasher (`set_password`).
* **`is_active`**: Boolean (Default True). Can the user log in?
* **`is_verified`**: Boolean (Default False). Have they verified their email?
* **`is_staff` / `is_superuser`**: Booleans for admin access.
* **`date_joined`**: DateTime.
* **`password_changed_at`**: DateTime. **Crucial for stateless JWT invalidation.**

```python
# identity/models/user.py
import uuid

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("Users must have an email address.")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        extra_fields.setdefault("is_verified", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_verified", True)
        return self._create_user(email, password, **extra_fields)


class User(AbstractBaseUser):
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

    def change_password(self, new_password):
        self.set_password(new_password)
        self.password_changed_at = timezone.now()
        self.save(update_fields=["password", "password_changed_at"])
```

## Related documents
- [Overview](../overview.md)
- [Token Management & Security](token-management.md)
- [Authentication & Sessions](authentication-and-sessions.md)
- [Account Lifecycle & Events](account-lifecycle.md)
- [Single Sign-On (SSO)](sso.md)
