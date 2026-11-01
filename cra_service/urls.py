from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

from cra_service.api import api

urlpatterns = [
    path("admin/", admin.site.urls),
    # The console (Ledger): pages for a manufacturer's security team, signed in with a session.
    path("console", RedirectView.as_view(url="/console/")),
    path("console/", include("console.urls")),
    path("", api.urls),
]

# Errors raised outside the API (e.g. in middleware) still return problem+json.
handler500 = "cra_service.errors.server_error"
