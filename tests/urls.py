from django.urls import path

from cra_service.urls import urlpatterns as service_urlpatterns
from tests.demo_api import demo, django_crash

urlpatterns = [
    path("demo/", demo.urls),
    path("django-crash", django_crash),
    *service_urlpatterns,
]

handler500 = "cra_service.errors.server_error"
