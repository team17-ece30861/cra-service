from django.contrib import admin
from django.urls import path

from cra_service.api import api

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", api.urls),
]

# Errors raised outside the API (e.g. in middleware) still return problem+json.
handler500 = "cra_service.errors.server_error"
