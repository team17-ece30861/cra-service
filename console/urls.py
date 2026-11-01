from django.urls import path

from console import views

app_name = "console"

urlpatterns = [
    path("", views.tickets, name="tickets"),
    path("sign-in", views.sign_in, name="sign-in"),
    path("sign-out", views.sign_out, name="sign-out"),
]
