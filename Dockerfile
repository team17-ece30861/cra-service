FROM python:3.12-slim

# DB_CONN_MAX_AGE: each gunicorn worker keeps its database connection for 300 s
# instead of opening one per request (cra_service/settings.py explains why that is safe
# with Neon's pooler, and why local runserver keeps the default of 0).
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080 \
    DB_CONN_MAX_AGE=300

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Admin static files are baked into the image and served by WhiteNoise.
# These values exist only for the build step; real ones come from Secret Manager.
RUN DATABASE_URL=sqlite:////tmp/build.db DJANGO_SECRET_KEY=build-only \
    python manage.py collectstatic --noinput

RUN useradd --create-home app
USER app

# Cloud Run sets $PORT. Access logs (gunicorn.conf.py) record the client, method,
# path, and status, never tokens or bodies. The timeout covers a full tester run
# (tester/runner.py).
CMD exec gunicorn cra_service.wsgi:application --config gunicorn.conf.py \
    --bind 0.0.0.0:$PORT --workers 2 --timeout 1800
