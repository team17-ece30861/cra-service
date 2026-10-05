from django.urls import path

from config.urls import urlpatterns as service_urlpatterns
from tests.demo_api import demo, django_crash

urlpatterns = [
    path("demo/", demo.urls),
    path("django-crash", django_crash),
    *service_urlpatterns,
]

handler500 = "core.errors.server_error"
