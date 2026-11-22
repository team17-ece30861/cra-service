"""Django settings. All configuration comes from environment variables.

Required: DATABASE_URL, DJANGO_SECRET_KEY
Optional: DJANGO_DEBUG (default false), ALLOWED_HOSTS (comma-separated),
          API_TOKEN_<NAME> (one bearer token per client, for every route except
          GET /health; when none is set, every protected request is rejected),
          API_TOKEN (older single token, accepted as client "default"),
          TESTER_TARGET_TOKENS (JSON: tokens our tester sends to other systems),
          TESTER_ALLOWED_HOSTS (comma-separated systems our tester may target),
          TESTER_OWN_SYSTEM_URLS (JSON list: exact own-system bases for model coverage),
          TESTER_MODEL_MAPPING_URL (published versioned design-to-test mapping)
          DB_CONN_MAX_AGE (seconds a worker keeps its database connection; default 0,
          the Docker image sets 300)
"""

import json
import os
from collections.abc import Mapping
from pathlib import Path

import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent


def env_bool(name: str, default: bool = False) -> bool:
    return os.environ.get(name, str(default)).strip().lower() in {"1", "true", "yes"}


def env_api_tokens(environ: Mapping[str, str]) -> dict[str, str]:
    """Bearer tokens by client name: API_TOKEN_TEAM21 is client "team21". API_TOKEN
    is client "default" so older .env files keep working; API_TOKEN_DEFAULT wins over
    it. Values are stripped because secrets created with `echo` carry a newline, and
    empty ones are ignored."""
    tokens = {}
    if token := environ.get("API_TOKEN", "").strip():
        tokens["default"] = token
    for key, value in sorted(environ.items()):
        name = key.removeprefix("API_TOKEN_").lower()
        if key.startswith("API_TOKEN_") and name and value.strip():
            tokens[name] = value.strip()
    return tokens


SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]
DEBUG = env_bool("DJANGO_DEBUG")
ALLOWED_HOSTS = [
    h.strip()
    for h in os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if h.strip()
]

API_TOKENS = env_api_tokens(os.environ)


def env_tester_tokens(raw: str) -> dict[str, str]:
    """Tokens our tester sends to other teams' systems: a JSON object mapping a target
    hostname (or full base URL) to its bearer token. Invalid JSON means none."""
    try:
        data = json.loads(raw or "{}")
    except ValueError:
        return {}
    if not isinstance(data, dict):
        return {}
    return {str(k).rstrip("/").lower(): str(v).strip() for k, v in data.items() if v}


TESTER_TARGET_TOKENS = env_tester_tokens(os.environ.get("TESTER_TARGET_TOKENS", ""))


def env_own_system_urls(raw: str) -> list[str]:
    try:
        values = json.loads(raw)
    except ValueError:
        return []
    if not isinstance(values, list):
        return []
    return [value for value in values if isinstance(value, str)]


TESTER_OWN_SYSTEM_URLS = env_own_system_urls(
    os.environ.get(
        "TESTER_OWN_SYSTEM_URLS",
        '["https://team17-dev-7zneiwx4ba-uc.a.run.app",'
        '"https://team17-prod-7zneiwx4ba-uc.a.run.app"]',
    )
)
# The published design-to-test mapping for model coverage, pinned to the commit that
# merged it (PR #106). The repository is public, so staff and podmates can open it.
# Change it together with acceptance/model_requirements.json's design version.
TESTER_MODEL_MAPPING_URL = os.environ.get(
    "TESTER_MODEL_MAPPING_URL",
    "https://github.com/team17-ece30861/cra-service/blob/"
    "e4e8e33cfadfd29a9e71137a94a37593258f6b5d/docs/model-coverage.md",
)

# Other teams' systems our tester may target, besides this service itself (the
# course spec: "approved pod service URLs"). Anything else is rejected with 400.
TESTER_ALLOWED_HOSTS = [
    h.strip().lower()
    for h in os.environ.get(
        "TESTER_ALLOWED_HOSTS", "cra-phase3.onrender.com,team21-cra-reporting-service.onrender.com"
    ).split(",")
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
    "tester",
    "console",
]

MIDDLEWARE = [
    # First, so it compresses the final response after every other middleware has
    # written the body (PlatformMiddleware rewrites error bodies). API responses only;
    # console pages are never compressed (see cra_service/compression.py).
    "cra_service.compression.ApiGZipMiddleware",
    "django.middleware.security.SecurityMiddleware",
    # Auth (401) and body size (413) run before routing so they take precedence
    # over 404/405, and every error response leaves as application/problem+json.
    "cra_service.middleware.PlatformMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "cra_service.urls"
# Unknown paths return 404 instead of redirecting to a trailing-slash variant.
APPEND_SLASH = False
WSGI_APPLICATION = "cra_service.wsgi.application"

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
                "console.context_processors.ledger",
            ],
        },
    },
]


# Neon: use the pooled connection string, which includes ?sslmode=require. The pooler
# is PgBouncer in transaction mode: each transaction (each autocommit query, or each
# atomic block) may run on a different Postgres backend. So nothing may rely on state
# that outlives a transaction, and that is true within one request as much as across
# requests; closing the connection after every request never protected it. What the
# code relies on, and why each is safe here:
# - No server-side cursors (they live across fetches): disabled below.
# - No prepared statements (named per backend): psycopg's prepare_threshold is None,
#   which Django already defaults to; set explicitly so it stays that way. Queries use
#   client-side binding (Django's default; server_side_binding stays off).
# - Locks: only transaction-scoped ones (SELECT ... FOR UPDATE, LOCK TABLE and
#   pg_advisory_xact_lock inside transaction.atomic). Never session-level advisory
#   locks or SET (only SET LOCAL).
# - Django's own TimeZone (SET at connect when it differs) and client_encoding (a
#   startup parameter) are parameters PgBouncer tracks per client and re-applies on
#   whichever backend serves it.
# So each gunicorn worker keeps its connection to the pooler (saving a TLS handshake and
# login per request, about 190 ms on Launchpad) for DB_CONN_MAX_AGE seconds since it
# opened; the first request after that reconnects. The Docker image sets 300. The
# default stays 0 because runserver handles each connection in a new thread, and
# connections kept by finished threads are never closed: locally they pile up until
# Postgres refuses clients (Django's docs say not to use persistent connections with
# the development server). Health checks run SELECT 1 before a reused connection's first
# query in each request and reconnect if the pooler or Neon dropped it, instead of
# failing that request. connect_timeout bounds each connection attempt (seconds), so an
# unreachable pooler fails the request instead of stalling a worker, and the tester's
# heartbeat, indefinitely.
def database_settings(environ: Mapping[str, str]) -> dict:
    database = dj_database_url.parse(
        environ["DATABASE_URL"],
        conn_max_age=int(environ.get("DB_CONN_MAX_AGE", "0")),
        conn_health_checks=True,
    )
    if database["ENGINE"] == "django.db.backends.postgresql":
        database["DISABLE_SERVER_SIDE_CURSORS"] = True
        database.setdefault("OPTIONS", {}).update(
            prepare_threshold=None, server_side_binding=False, connect_timeout=10
        )
    return database


DATABASES = {"default": database_settings(os.environ)}

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
# Console sign-in (4.U1). Sessions last 12 hours from sign-in, and the session and CSRF
# cookies only go to console pages, never with API requests.
LOGIN_URL = "/console/sign-in"
SESSION_COOKIE_AGE = 12 * 3600
SESSION_COOKIE_PATH = "/console/"
CSRF_COOKIE_PATH = "/console/"
# Nothing reads the CSRF token from JavaScript; forms carry it in a hidden field.
CSRF_COOKIE_HTTPONLY = True
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
