"""Django settings for the Auth microservice.

Configuration is driven by environment variables via ``django-environ``.
All secrets (JWT keys, Fernet key, database URL) are injected through the
environment; see ``.env.example`` for the full list.
"""

from pathlib import Path

import environ

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1"]),
    REDIS_PORT=(int, 6379),
    REDIS_PASSWORD=(str, ""),
    ALLOW_MULTI_DEVICE_REFRESH_TOKENS=(bool, False),
    LOG_LEVEL=(str, "INFO"),
)
environ.Env.read_env(BASE_DIR / ".env")

# ---------------------------------------------------------------------------
# Core Django
# ---------------------------------------------------------------------------
SECRET_KEY = env("SECRET_KEY")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env("ALLOWED_HOSTS")

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.admin",
    "identity",
]

MIDDLEWARE = [
    "identity.api.middleware.RequestIDMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
DATABASES = {"default": env.db("DATABASE_URL")}

# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
AUTH_USER_MODEL = "identity.User"

# Stateless API fronted by a gateway; sessions/CSRF are not used for auth.
# CSRF protection remains configured for the admin only.
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]

# ---------------------------------------------------------------------------
# Redis
# ---------------------------------------------------------------------------
REDIS_HOST = env("REDIS_HOST")
REDIS_PORT = env("REDIS_PORT")
REDIS_PASSWORD = env("REDIS_PASSWORD") or None

# ---------------------------------------------------------------------------
# JWT (RS256)
# ---------------------------------------------------------------------------
_JWT_PRIVATE_KEY_PATH = BASE_DIR / env(
    "JWT_PRIVATE_KEY_PATH", default="certs/private.pem"
)
_JWT_PUBLIC_KEY_PATH = BASE_DIR / env("JWT_PUBLIC_KEY_PATH", default="certs/public.pem")


def _read_key(path: Path) -> str:
    """Read a PEM key file, returning an empty string if it does not exist.

    This allows the project to import successfully before dev keys are
    generated (e.g. during ``uv sync`` or CI lint runs).
    """
    if path.exists():
        return path.read_text()
    return ""


JWT_PRIVATE_KEY = _read_key(_JWT_PRIVATE_KEY_PATH)
JWT_PUBLIC_KEY = _read_key(_JWT_PUBLIC_KEY_PATH)

# ---------------------------------------------------------------------------
# MFA (Fernet)
# ---------------------------------------------------------------------------
MFA_ENCRYPTION_KEY = env("MFA_ENCRYPTION_KEY", default="")

# ---------------------------------------------------------------------------
# Token policy
# ---------------------------------------------------------------------------
ALLOW_MULTI_DEVICE_REFRESH_TOKENS = env("ALLOW_MULTI_DEVICE_REFRESH_TOKENS")

# ---------------------------------------------------------------------------
# SSO - GitHub
# ---------------------------------------------------------------------------
GITHUB_CLIENT_ID = env("GITHUB_CLIENT_ID", default="")
GITHUB_CLIENT_SECRET = env("GITHUB_CLIENT_SECRET", default="")

# ---------------------------------------------------------------------------
# Static files
# ---------------------------------------------------------------------------
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Logging (12-Factor JSON to stdout)
# ---------------------------------------------------------------------------
LOG_LEVEL = env("LOG_LEVEL")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(asctime)s %(levelname)s %(name)s %(message)s %(request_id)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
            "stream": "ext://sys.stdout",
        },
    },
    "loggers": {
        "django": {"handlers": ["console"], "level": LOG_LEVEL, "propagate": False},
        "identity": {"handlers": ["console"], "level": LOG_LEVEL, "propagate": False},
    },
    "root": {"handlers": ["console"], "level": LOG_LEVEL},
}
