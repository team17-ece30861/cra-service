FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

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

# Cloud Run sets $PORT. Access logs record method, path, and status, never bodies.
CMD exec gunicorn cra_service.wsgi:application \
    --bind 0.0.0.0:$PORT --workers 2 --timeout 30 --access-logfile -
