"""Django settings. All configuration comes from environment variables.

Required: DATABASE_URL, DJANGO_SECRET_KEY
Optional: DJANGO_DEBUG (default false), ALLOWED_HOSTS (comma-separated)
"""

import os
from pathlib import Path

import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent


def env_bool(name: str, default: bool = False) -> bool:
    return os.environ.get(name, str(default)).strip().lower() in {"1", "true", "yes"}


SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]
DEBUG = env_bool("DJANGO_DEBUG")
ALLOWED_HOSTS = [
    h.strip()
    for h in os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if h.strip()
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "core",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

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

# Neon: use the pooled connection string, which includes ?sslmode=require.
# The pooler runs in transaction mode, so Django must not hold connections
# open or use server-side cursors.
DATABASES = {"default": dj_database_url.parse(os.environ["DATABASE_URL"], conn_max_age=0)}
if DATABASES["default"]["ENGINE"] == "django.db.backends.postgresql":
    DATABASES["default"]["DISABLE_SERVER_SIDE_CURSORS"] = True

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# All times are UTC, end to end.
USE_TZ = True
TIME_ZONE = "UTC"
LANGUAGE_CODE = "en-us"
USE_I18N = False

# Static files (admin only), served by WhiteNoise from inside the container.
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

# Cloud Run terminates HTTPS in front of the container.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_HSTS_SECONDS = 0 if DEBUG else 3600
# Cloud Run only serves HTTPS on *.run.app, so Django doesn't need to redirect.
# HSTS subdomain/preload settings apply to domains we own; *.run.app is Google's.
SILENCED_SYSTEM_CHECKS = ["security.W008", "security.W005", "security.W021"]

# Log to stdout so Cloud Run captures it. Never log request bodies
# (reporter confidentiality).
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
}
