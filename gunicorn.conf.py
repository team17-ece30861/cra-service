"""Gunicorn settings, loaded by the Dockerfile's CMD."""

# One line per request on stdout, which Cloud Run captures. Apache's combined format,
# except the user field is the client whose token matched (set by
# cra_service.middleware; "-" when none did). Gunicorn's default user field decodes
# Basic credentials, so it could log a token. Never add the Authorization header
# (%({authorization}i)s) or anything from the request body.
accesslog = "-"
access_log_format = (
    '%(h)s %(l)s %({cra_service.client}e)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'
)
