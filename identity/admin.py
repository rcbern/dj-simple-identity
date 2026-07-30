"""Django admin registrations for the Identity app."""

from django.contrib import admin

from identity.models.mfa import UserMFA
from identity.models.sso import SocialAccount
from identity.models.token import Token
from identity.models.user import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    """Admin view for the custom User model."""

    list_display = ("email", "is_active", "is_verified", "is_staff", "date_joined")
    search_fields = ("email",)
    list_filter = ("is_active", "is_verified", "is_staff", "is_superuser")
    ordering = ("-date_joined",)


@admin.register(Token)
class TokenAdmin(admin.ModelAdmin):
    """Admin view for the Token model."""

    list_display = (
        "user",
        "token_type",
        "expires_at",
        "created_at",
    )
    list_filter = ("token_type",)
    search_fields = ("user__email",)
    ordering = ("-created_at",)


@admin.register(UserMFA)
class UserMFAAdmin(admin.ModelAdmin):
    """Admin view for the UserMFA model."""

    list_display = ("user", "mfa_type", "is_enabled", "created_at")
    list_filter = ("mfa_type", "is_enabled")
    search_fields = ("user__email",)


@admin.register(SocialAccount)
class SocialAccountAdmin(admin.ModelAdmin):
    """Admin view for the SocialAccount model."""

    list_display = ("user", "provider", "provider_user_id", "provider_email")
    list_filter = ("provider",)
    search_fields = ("user__email", "provider_email", "provider_user_id")
