from django.urls import path

from console import views, views_forms

app_name = "console"

urlpatterns = [
    path("", views.tickets, name="tickets"),
    path("sign-in", views.sign_in, name="sign-in"),
    path("sign-out", views.sign_out, name="sign-out"),
    # Before tickets/<id>, which would otherwise take "new" as a ticket ID.
    path("tickets/new", views_forms.new_ticket, name="new-ticket"),
    path("tickets/<str:ticket_id>", views.ticket, name="ticket"),
    path("tickets/<str:ticket_id>/edit", views_forms.edit_ticket, name="edit-ticket"),
    path("tickets/<str:ticket_id>/triage", views_forms.triage, name="triage"),
]
